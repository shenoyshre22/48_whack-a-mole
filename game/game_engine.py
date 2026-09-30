import io
import math
import random
import struct
import wave

import pygame
from .hole import Hole

# Game Engine

DARK_BROWN = (60, 40, 20)
MOLE_BROWN = (140, 95, 55)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GAME_OVER_RED = (150, 35, 35)
BUTTON_GREEN = (45, 110, 65)
BUTTON_RED = (125, 45, 45)
BUTTON_BLUE = (45, 85, 135)
BUTTON_HOVER = (220, 190, 80)

class GameEngine:
    def __init__(self, width, height, rows=3, cols=3):
        self.width = width
        self.height = height

        self.holes = []
        spacing_x = width // (cols + 1)
        spacing_y = (height - 80) // (rows + 1)
        for r in range(rows):
            for c in range(cols):
                cx = spacing_x * (c + 1)
                cy = 80 + spacing_y * (r + 1)
                self.holes.append(Hole(cx, cy))

        self.spawn_chance = 0.02   # per-hole, per-frame chance to pop up
        self.mole_up_frames = 45   # how long a mole stays up if not whacked
        self.difficulty_profiles = {
            "Easy": {"max_moles": 2, "speed": 1, "spawn_chance": 0.02},
            "Medium": {"max_moles": 4, "speed": 2, "spawn_chance": 0.035},
            "Hard": {"max_moles": 7, "speed": 3, "spawn_chance": 0.05},
        }
        self.difficulty = "Easy"
        self.max_moles = 2

        self.round_seconds = 30
        self.time_left_frames = self.round_seconds * 60

        self.score = 0
        self.misses = 0
        self.font = pygame.font.SysFont("Arial", 28)
        sci_fi_font = pygame.font.match_font(
            ["Press Start 2P", "Orbitron", "Eurostile", "BankGothic", "DejaVu Sans Mono"]
        )
        self.game_over_font = pygame.font.Font(sci_fi_font, 52) if sci_fi_font else pygame.font.SysFont("Arial", 52, bold=True)
        self.button_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.game_over = False
        self.exit_requested = False
        self.sounds = self._create_sounds()
        button_y = height // 2 + 55
        self.difficulty_buttons = {
            "Easy": pygame.Rect(20, button_y, 145, 52),
            "Medium": pygame.Rect(177, button_y, 145, 52),
            "Hard": pygame.Rect(334, button_y, 145, 52),
        }
        self.exit_button = pygame.Rect(width // 2 - 75, button_y + 65, 150, 48)

        self._set_difficulty(self.difficulty)

    def _create_sounds(self):
        """Create small effects in memory so missing audio files cannot break the game."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return {
                "hit": self._make_sound(((660, 0.07), (990, 0.09))),
                "miss": self._make_sound(((180, 0.16), (110, 0.12))),
                "game_over": self._make_sound(((440, 0.16), (330, 0.18), (220, 0.24))),
            }
        except (pygame.error, OSError):
            return {}

    @staticmethod
    def _make_sound(notes):
        sample_rate = 44100
        samples = bytearray()
        for frequency, duration in notes:
            sample_count = int(sample_rate * duration)
            for sample_index in range(sample_count):
                envelope = 1 - (sample_index / sample_count)
                value = int(32767 * 0.25 * envelope * math.sin(
                    2 * math.pi * frequency * sample_index / sample_rate
                ))
                samples.extend(struct.pack("<h", value))

        audio_file = io.BytesIO()
        with wave.open(audio_file, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples)
        audio_file.seek(0)
        return pygame.mixer.Sound(file=audio_file)

    def _play_sound(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    def handle_event(self, event):
        if self.game_over:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for difficulty, button in self.difficulty_buttons.items():
                    if button.collidepoint(event.pos):
                        self.reset(difficulty)
                        return
                if self.exit_button.collidepoint(event.pos):
                    self.exit_requested = True
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_click(event.pos)

    def _set_difficulty(self, difficulty):
        profile = self.difficulty_profiles[difficulty]
        self.difficulty = difficulty
        self.max_moles = profile["max_moles"]
        self.spawn_chance = profile["spawn_chance"]
        self.mole_up_frames = 45 // profile["speed"]

    def reset(self, difficulty=None):
        if difficulty is not None:
            self._set_difficulty(difficulty)
        self.score = 0
        self.misses = 0
        self.time_left_frames = self.round_seconds * 60
        self.game_over = False
        self.exit_requested = False
        for hole in self.holes:
            hole.active = False
            hole.timer = 0

    def _handle_click(self, pos):
        candidates = [
            hole
            for hole in self.holes
            if hole.active and hole.rect().collidepoint(pos)
        ]

        if candidates:
            clicked_hole = min(
                candidates,
                key=lambda hole: (
                    hole.center_x - pos[0]
                ) ** 2 + (hole.center_y - pos[1]) ** 2,
            )
            clicked_hole.whack()
            self.score += 1
            self._play_sound("hit")
        else:
            self.misses += 1
            self._play_sound("miss")

    def handle_input(self):
        # Reserved for continuously-held-key input; this game is
        # entirely mouse-driven, so there's nothing to poll here.
        pass

    def update(self):
        if self.game_over:
            return

        self.time_left_frames -= 1
        if self.time_left_frames <= 0:
            self.game_over = True
            self._play_sound("game_over")
            return

        for hole in self.holes:
            hole.update()
        active_moles = sum(hole.active for hole in self.holes)
        for hole in self.holes:
            if (
                active_moles < self.max_moles
                and not hole.active
                and random.random() < self.spawn_chance
            ):
                hole.pop_up(self.mole_up_frames)
                active_moles += 1

    def render(self, screen):
        for hole in self.holes:
            pygame.draw.circle(screen, DARK_BROWN, (hole.center_x, hole.center_y), 40)
            if hole.active:
                pygame.draw.circle(screen, MOLE_BROWN, (hole.center_x, hole.center_y), 32)

        score_text = self.font.render(f"Score: {self.score}", True, BLACK)
        screen.blit(score_text, (10, 10))

        seconds_left = max(0, self.time_left_frames // 60)
        timer_text = self.font.render(f"Time: {seconds_left}s", True, BLACK)
        screen.blit(timer_text, (self.width - 140, 10))

        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            screen.blit(overlay, (0, 0))

            title = self.game_over_font.render("GAME OVER", True, GAME_OVER_RED)
            title_outline = self.game_over_font.render("GAME OVER", True, WHITE)
            title_position = title.get_rect(center=(self.width // 2, self.height // 2 - 75))
            for offset in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                screen.blit(title_outline, title_position.move(offset))
            screen.blit(title, title_position)

            final_score = self.font.render(f"FINAL SCORE: {self.score}", True, WHITE)
            screen.blit(final_score, final_score.get_rect(center=(self.width // 2, self.height // 2 - 5)))

            prompt = self.button_font.render("RETRY? CHOOSE DIFFICULTY", True, WHITE)
            screen.blit(prompt, prompt.get_rect(center=(self.width // 2, self.height // 2 + 38)))

            mouse_position = pygame.mouse.get_pos()
            button_colors = {"Easy": BUTTON_GREEN, "Medium": BUTTON_BLUE, "Hard": GAME_OVER_RED}
            for difficulty, button in self.difficulty_buttons.items():
                self._draw_button(
                    screen,
                    button,
                    difficulty,
                    button_colors[difficulty],
                    mouse_position,
                )
            self._draw_button(screen, self.exit_button, "END GAME", BUTTON_RED, mouse_position)

    def _draw_button(self, screen, button, label, color, mouse_position):
        button_color = BUTTON_HOVER if button.collidepoint(mouse_position) else color
        pygame.draw.rect(screen, button_color, button)
        pygame.draw.rect(screen, WHITE, button, 2)
        text = self.button_font.render(label, True, WHITE)
        text_rect = text.get_rect(center=button.center)
        screen.blit(text, text_rect)
