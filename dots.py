import matplotlib.pyplot as plt
import random
from math import sin, cos, dist

board = []

#for x in range(-50//2,50//2,6):
	#for y in range(-50//2,50//2,6):

for r in range(0,100,5):
	r = r/3*10 + random.random()*10
	x = sin(r)*30
	y = cos(r)*30
	board.append([x+1.15*random.random(),y+1.15*random.random(), 100*random.random(), 3*random.random()+3, random.choice(['ro'])])

for r in range(0,100,5):
	r = r/3*10 + random.random()*10
	x = sin(r)*30 + 30
	y = cos(r)*30 + 30
	board.append([x+1.15*random.random(),y+1.15*random.random(), 100*random.random(), 3*random.random()+3, random.choice(['yo'])])

def draw_board(board, c='ro', s=0.3):
	for dot in board:
		plt.plot(dot[0],dot[1],dot[4], markersize=dot[3]) 
		
def get_forces(board, idx):
	x = 0
	y = 0
	for i, value in enumerate(board):
		if i != idx:
			xp = -( board[idx][0] - board[i][0] )/dist(board[idx][0:2], board[i][0:2]) * (1/ (dist(board[idx][0:2], board[i][0:2])+22)**2)
			yp =  -( board[idx][1] - board[i][1] )/dist(board[idx][0:2], board[i][0:2]) * (1/ (dist(board[idx][0:2], board[i][0:2])+22)**2)
			x += xp
			y += yp
	return x*10, y*10

def update_board(board):
	nboard = []
	for i, dot in enumerate(board):
		x, y = get_forces(board, i)
		#print(x,y)
		nboard.append([ dot[0]+x+sin(dot[2])/20,
							 dot[1]+y+cos(dot[2])/20,
							 dot[2] + 0.006,
							 (dot[3]-0.01)/1.002,
							 dot[4]
							 ])
	return nboard
	
#draw_board(board, 'bo', 5)

for i in range(500):
	board = update_board(board)
	draw_board(board)

#draw_board(board, 'go', 5)

plt.show()