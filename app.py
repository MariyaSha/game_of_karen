import pygame

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
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.blit(bg, (0,0))
    screen.blit(karen, player_pos)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player_pos.x -= 5
    if keys[pygame.K_RIGHT]:
        player_pos.x += 5

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
