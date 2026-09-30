import pygame
import random
from .hole import Hole

# Game Engine

DARK_BROWN = (60, 40, 20)
MOLE_BROWN = (140, 95, 55)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GAME_OVER_RED = (150, 35, 35)
BUTTON_GREEN = (45, 110, 65)
BUTTON_RED = (125, 45, 45)
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
        self.retry_button = pygame.Rect(width // 2 - 145, height // 2 + 55, 125, 52)
        self.exit_button = pygame.Rect(width // 2 + 20, height // 2 + 55, 125, 52)

    def handle_event(self, event):
        if self.game_over:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.retry_button.collidepoint(event.pos):
                    self.reset()
                elif self.exit_button.collidepoint(event.pos):
                    self.exit_requested = True
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_click(event.pos)

    def reset(self):
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
        else:
            self.misses += 1

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
            return

        for hole in self.holes:
            hole.update()
            if not hole.active and random.random() < self.spawn_chance:
                hole.pop_up(self.mole_up_frames)

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

            mouse_position = pygame.mouse.get_pos()
            self._draw_button(screen, self.retry_button, "RETRY?", BUTTON_GREEN, mouse_position, retry=True)
            self._draw_button(screen, self.exit_button, "END GAME", BUTTON_RED, mouse_position)

    def _draw_button(self, screen, button, label, color, mouse_position, retry=False):
        button_color = BUTTON_HOVER if button.collidepoint(mouse_position) else color
        pygame.draw.rect(screen, button_color, button)
        pygame.draw.rect(screen, WHITE, button, 2)
        text = self.button_font.render(label, True, WHITE)
        text_rect = text.get_rect(center=button.center)
        if retry:
            icon_center = (button.left + 24, button.centery)
            pygame.draw.arc(screen, WHITE, (icon_center[0] - 10, icon_center[1] - 10, 20, 20), 0.4, 5.5, 3)
            pygame.draw.polygon(screen, WHITE, [(icon_center[0] - 10, icon_center[1] - 7), (icon_center[0] - 2, icon_center[1] - 11), (icon_center[0] - 3, icon_center[1] - 3)])
            text_rect.centerx += 10
        screen.blit(text, text_rect)
