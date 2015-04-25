__author__ = 'Bim'
import math
#size of the map
MAP_WIDTH = 43
MAP_HEIGHT = 26

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

def is_blocked(x, y):
	#first test the map tile
	if map[x][y].blocked:
		return True

	#now check for any blocking objects
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True

	return False

