# Example file showing a circle moving on screen
import pygame

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1376, 768))
clock = pygame.time.Clock()
running = True

bg_img = pygame.image.load(
        "assets/background.png"
    ).convert()

bg = pygame.transform.smoothscale(
        bg_img, (1376, 768)
    )

karen_img = pygame.image.load(
        "assets/karen1_walk_right.png"
    ).convert_alpha()

karen = pygame.transform.smoothscale(
        karen_img, (200, 200)
    )

player_pos = pygame.Vector2(
    200, 500
    )

while running:
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # fill the screen with a color to wipe away anything from last frame
    screen.blit(bg, (0,0))
    screen.blit(karen, player_pos)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_a]:
        player_pos.x -= 5
    if keys[pygame.K_d]:
        player_pos.x += 5

    # flip() the display to put your work on screen
    pygame.display.flip()
    clock.tick(60)

pygame.quit()