from gtts import gTTS
import pygame
tts = gTTS(text='Hello, Aaron. Hello, David', lang='en', slow=True)
tts.save("E:/Google Drive/Github/tempdata/ProprioprostheticsBehavioralControl/bla.mp3")

pygame.mixer.init()
welcomeChime = pygame.mixer.Sound("E:\\Google Drive\\Github\\tempdata\\ProprioprostheticsBehavioralControl\\hello.wav")
welcomeChime.set_volume(0.1)
welcomeChime.play()
