#!/usr/bin/python
#
# libtcod python tutorial
#

import libtcodpy as libtcod
import os
import math
import textwrap
import random
import shelve
import mapcreate
import maps


#actual size of the window
SCREEN_WIDTH = 59
SCREEN_HEIGHT = 35

#size of the map
MAP_WIDTH = 43
MAP_HEIGHT = 26

CAMERA_WIDTH = 43
CAMERA_HEIGHT = 26

#sizes and coordinates relevant for the GUI
BAR_WIDTH = 14
PANEL_HEIGHT = 9
PANEL_WIDTH = 8
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
PANEL_X = SCREEN_WIDTH - PANEL_WIDTH

SIDEBAR_HEIGHT = SCREEN_HEIGHT
SIDEBAR_WIDTH = 16
SIDEBAR_Y = 0
SIDEBAR_X = 43


MSG_X = 1
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 4
MSG_HEIGHT = PANEL_HEIGHT - 2
INVENTORY_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 40
LEVEL_SCREEN_WIDTH = 50


#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
 
#spell values
HEAL_AMOUNT = 40
LIGHTNING_DAMAGE = 40
LIGHTNING_RANGE = 5
CONFUSE_RANGE = 8
CONFUSE_NUM_TURNS = 10
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 25
 
#experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150
 
 
FOV_ALGO = 0  #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not
TORCH_RADIUS = 8
 
LIMIT_FPS = 26  #20 frames-per-second maximum
 
 
color_dark_wall = libtcod.Color(0, 0, 10)
color_light_wall = libtcod.Color(50, 50, 50)
color_dark_ground = libtcod.Color(0, 0, 0)
color_light_ground = libtcod.Color(22, 22, 22)
 
 
class Tile:
	#a tile of the map and its properties
	def __init__(self, blocked, sludge, bar, door, space, block_sight=None):
		self.blocked = blocked

		self.sludge = sludge
		self.bar = bar
		self.door = door
		self.space = space

		#all tiles start unexplored
		self.explored = False

		#by default, if a tile is blocked, it also blocks sight
		if block_sight is None: block_sight = blocked
		self.block_sight = block_sight
 
class Rect:
	#a rectangle on the map. used to characterize a room.
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h
 
	def center(self):
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)
 
	def intersect(self, other):
		#returns true if this rectangle intersects with another one
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and
				self.y1 <= other.y2 and self.y2 >= other.y1)
 
class Object:
	#this is a generic object: the player, a monster, an item, the stairs...
	#it's always represented by a character on screen.
	def __init__(self, x, y, char, name, color, desc=None, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		self.desc = desc
		self.blocks = blocks
		self.always_visible = always_visible
		self.fighter = fighter
		if self.fighter:  #let the fighter component know who owns it
			self.fighter.owner = self
 
		self.ai = ai
		if self.ai:  #let the AI component know who owns it
			self.ai.owner = self
 
		self.item = item
		if self.item:  #let the Item component know who owns it
			self.item.owner = self
 
		self.equipment = equipment
		if self.equipment:  #let the Equipment component know who owns it
			self.equipment.owner = self
 
			#there must be an Item component for the Equipment component to work properly
			self.item = Item()
			self.item.owner = self
 
	def move(self, dx, dy):
		#move by the given amount, if the destination is not blocked
		if not is_blocked(self.x + dx, self.y + dy):
			self.x += dx
			self.y += dy

	def distance_to(self, other):
		#return the distance to another object
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)
 
	def distance(self, x, y):
		#return the distance to some coordinates
		return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
 
	def send_to_back(self):
		#make this object be drawn first, so all others appear above it if they're in the same tile.
		global objects
		objects.remove(self)
		objects.insert(0, self)
 
	def draw(self):
		#only show if it's visible to the player; or it's set to "always visible" and on an explored tile
		if libtcod.map_is_in_fov(fov_map, self.x, self.y):
			(x, y) = to_camera_coordinates(self.x, self.y)

			if x is not None:
				#set the color and then draw the character that represents this object at its position
				libtcod.console_set_default_foreground(con, self.color)
				libtcod.console_put_char(con, x, y, self.char, libtcod.BKGND_NONE)

	def clear(self):
		(x, y) = to_camera_coordinates(self.x, self.y)
		if x is not None:
		#erase the character that represents this object
			libtcod.console_put_char(con, x, y, ' ', libtcod.BKGND_NONE)

class Furniture:
#an item that can be picked up and used.
	def __init__(self, use_function=None, opened=False):
		self.use_function = use_function
		self.opened = opened

	def use(self):
		#just call the "use_function" if it is defined
		if self.use_function is None:
			message('The ' + self.owner.name + ' cannot be used.')

 
class Fighter:
	#combat-related properties and methods (monster, player, NPC).
	def __init__(self, my_path, lastx, lasty, hp, defense, power, xp, flicker, death_function=None):
		self.my_path = my_path
		self.lastx = lastx
		self.lasty = lasty

		self.base_max_hp = hp
		self.hp = hp
		self.base_defense = defense
		self.base_power = power
		self.xp = xp
		self.death_function = death_function

		self.flicker = flicker
 		if isinstance(death_function, str):
			self.death_function = globals()[death_function]
		else:
			self.death_function = death_function
	@property
	def power(self):  #return actual power, by summing up the bonuses from all equipped items
		bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
		return self.base_power + bonus
 
	@property
	def defense(self):  #return actual defense, by summing up the bonuses from all equipped items
		bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
		return self.base_defense + bonus
 
	@property
	def max_hp(self):  #return actual max_hp, by summing up the bonuses from all equipped items
		bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_hp + bonus

	def move_towards(self, target_x, target_y):
		#get yo' a-star on in a fistful of code?!  this lib is awesome!

		#if no path exists yet, get right onto that, stat!
		if self.my_path is 0:
			self.my_path = libtcod.path_new_using_map(fov_map, 1.0)

		reblock = False

		#need some logic here...constantly refresh path seems omniscient and computationally expensive

		if not libtcod.map_is_walkable(fov_map, target_x, target_y):
			reblock = True

		libtcod.map_set_properties(fov_map, target_x, target_y, True, True)	#momentarily set the target to unblocked so the pathing works. kludgy, I know, but easier than writing my own a*!!!!

		libtcod.path_compute(self.my_path, self.owner.x, self.owner.y, target_x, target_y)

		if reblock:
			libtcod.map_set_properties(fov_map, target_x, target_y, True, False) #kludge moment over. resume normal viewing!

		if not libtcod.path_is_empty(self.my_path):
			x, y = libtcod.path_walk(self.my_path,True)
			if x and not is_blocked(x,y) and libtcod.path_size(self.my_path) < 10: #more than ten is too far, don't worry about it
				libtcod.map_set_properties(fov_map, self.owner.x, self.owner.y, True, True)
				self.owner.x = x
				self.owner.y = y
				libtcod.map_set_properties(fov_map, x, y, True, False)
			else:
				self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))

	def attack(self, target):
		#a simple formula for attack damage
		damage = self.power - target.fighter.defense
 
		if damage > 0:
			#make the target take some damage
			if self.owner == player:
				message(self.owner.name.capitalize() + ' attacks the ' + target.name + ' for ' + str(damage) + ' hit points.')
				target.fighter.take_damage(damage)
			else:
				message('The ' + self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
				target.fighter.take_damage(damage)

		else:
			if self.owner == player:
				message(self.owner.name.capitalize() + ' attacks the ' + target.name + ' but it has no effect!')
			else:
				message('The ' + self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')
 
	def take_damage(self, damage):
		#apply damage if possible
		if damage > 0:
			self.hp -= damage
			self.flicker = 1

			if self.hp <= 4 and self.hp > 0 :
				if self.owner == player:
					message(self.owner.name.capitalize() + ' looks badly wounded!')
				else:
					message('The ' + self.owner.name.capitalize() + ' looks badly wounded!')


			#check for death. if there's a death function, call it
			if self.hp <= 0:
				function = self.death_function
				if function is not None:
					function(self.owner)
				if self.owner != player:  #yield experience to the player
					player.fighter.xp += self.xp
 
	def heal(self, amount):
		#heal by the given amount, without going over the maximum
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp

class BasicMonster:
	#AI for a basic monster.
	def take_turn(self):
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			#if sees player, stores location
			monster.fighter.lastx = player.x
			monster.fighter.lasty = player.y

			if monster.distance_to(player) >= 2:
				monster.fighter.move_towards(player.x, player.y)

			elif player.fighter.hp > 0:
				monster.fighter.attack(player)
 
class ConfusedMonster:
	#AI for a temporarily confused monster (reverts to previous AI after a while).
	def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns
 
	def take_turn(self):
		if self.num_turns > 0:  #still confused...
			#move in a random direction, and decrease the number of turns confused
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.num_turns -= 1
 
		else:  #restore the previous AI (this one will be deleted because it's not referenced anymore)
			self.owner.ai = self.old_ai
			message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)
 
class Item:
	#an item that can be picked up and used.
	def __init__(self, use_function=None):
		self.use_function = use_function
 
	def pick_up(self):
		#add to the player's inventory and remove from the map
		if len(inventory) >= 26:
			message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You picked up a ' + self.owner.name + '!', libtcod.green)
 
			#special case: automatically equip, if the corresponding equipment slot is unused
			equipment = self.owner.equipment
			if equipment and get_equipped_in_slot(equipment.slot) is None:
				equipment.equip()
 
	def drop(self):
		#special case: if the object has the Equipment component, dequip it before dropping
		if self.owner.equipment:
			self.owner.equipment.dequip()
 
		#add to the map and remove from the player's inventory. also, place it at the player's coordinates
		objects.append(self.owner)
		inventory.remove(self.owner)
		self.owner.x = player.x
		self.owner.y = player.y
		message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
 
	def use(self):
		#special case: if the object has the Equipment component, the "use" action is to equip/dequip
		if self.owner.equipment:
			self.owner.equipment.toggle_equip()
			return
 
		#just call the "use_function" if it is defined
		if self.use_function is None:
			message('The ' + self.owner.name + ' cannot be used.')
		else:
			if self.use_function() != 'cancelled':
				inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
 
class Equipment:
	#an object that can be equipped, yielding bonuses. automatically adds the Item component.
	def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0):
		self.power_bonus = power_bonus
		self.defense_bonus = defense_bonus
		self.max_hp_bonus = max_hp_bonus
 
		self.slot = slot
		self.is_equipped = False
 
	def toggle_equip(self):  #toggle equip/dequip status
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()
 
	def equip(self):
		#if the slot is already being used, dequip whatever is there first
		old_equipment = get_equipped_in_slot(self.slot)
		if old_equipment is not None:
			old_equipment.dequip()
 
		#equip object and show a message about it
		self.is_equipped = True
		message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
 
	def dequip(self):
		#dequip object and show a message about it
		if not self.is_equipped: return
		self.is_equipped = False
		message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
 

def create_room(room):
	global map
	#go through the tiles in the rectangle and make them passable
	for x in range(room.x1 + 1, room.x2):
		for y in range(room.y1 + 1, room.y2):
			map[x][y].blocked = False
			map[x][y].block_sight = False

def create_boundaries():
	for y in range(MAP_HEIGHT):
		map[0][y].blocked = True
		map[0][y].block_sight = True
		map[69][y].blocked = True
		map[69][y].block_sight = True
	for x in range(MAP_WIDTH):
		map[x][0].blocked = True
		map[x][0].block_sight = True
		map[x][31].blocked = True
		map[x][31].block_sight = True
						#kludgy boundary because map is rubbish.

def create_circular_room(room):
	global map
	#center of circle
	cx = (room.x1 + room.x2) / 2
	cy = (room.y1 + room.y2) / 2

	#radius of circle: make it fit nicely inside the room, by making the
	#radius be half the width or height (whichever is smaller)
	width = room.x2 - room.x1
	height = room.y2 - room.y1
	r = min(width, height) / 1.8

	#go through the tiles in the circle and make them passable
	for x in range(room.x1, room.x2 + 1):
		for y in range(room.y1, room.y2 + 1):
			if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) <= r:
				map[x][y].blocked = False
				map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
	global map
	#horizontal tunnel. min() and max() are used in case x1>x2
	for x in range(min(x1, x2), max(x1, x2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
	global map
	#vertical tunnel
	for y in range(min(y1, y2), max(y1, y2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def get_equipped_in_slot(slot):  #returns the equipment in a slot, or None if it's empty
	for obj in inventory:
		if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
			return obj.equipment
	return None
 
def get_all_equipped(obj):  #returns a list of equipped items
	if obj == player:
		equipped_list = []
		for item in inventory:
			if item.equipment and item.equipment.is_equipped:
				equipped_list.append(item.equipment)
		return equipped_list
	else:
		return []  #other objects have no equipment

def is_blocked(x, y):
	#first test the map tile
	if map[x][y].blocked:
		return True

	#now check for any blocking objects
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True

	return False

def sightblocked (x, y):
	map[x][y].block_sight = True

def move_camera(target_x, target_y):
	global camera_x, camera_y, fov_recompute

	#new camera coordinates (top-left corner of the screen relative to the map)
	x = target_x - CAMERA_WIDTH / 2  #coordinates so that the target is at the center of the screen
	y = target_y - CAMERA_HEIGHT / 2

	#make sure the camera doesn't see outside the map
	if x < 0: x = 0
	if y < 0: y = 0
	if x > MAP_WIDTH - CAMERA_WIDTH - 1: x = MAP_WIDTH - CAMERA_WIDTH - 1
	if y > MAP_HEIGHT - CAMERA_HEIGHT - 1: y = MAP_HEIGHT - CAMERA_HEIGHT - 1

	if x != camera_x or y != camera_y: fov_recompute = True

	(camera_x, camera_y) = (x, y)
	initialize_fov()

def to_camera_coordinates(x, y):
	#convert coordinates on the map to coordinates on the screen
	(x, y) = (x - camera_x, y - camera_y)

	if (x < 0 or y < 0 or x >= CAMERA_WIDTH or y >= CAMERA_HEIGHT):
		return (None, None)  #if it's outside the view, return nothing

	return (x, y)

class MonsterDataListener:
	def new_struct(self, struct, name):
		global monster_data
		self.current_name = name
		monster_data[name] = {}
		return True

	def new_flag(self, name):
		global monster_data
		monster_data[self.current_name][name] = True
		return True

	def new_property(self,name, typ, value):
		global monster_data
		monster_data[self.current_name][name] = value
		return True

	def end_struct(self, struct, name):
		self.current_name = None
		return True

	def error(self,msg):
		global monster_data
		print 'Monster data parser error : ', msg
		if self.current_name is not None:
			del monster_data[self.current_name]
			self.current_name = None
		return True

def make_map():
	global map, objects, stairs, upstairs, factorystairs, factoryexitstairs, MAP_HEIGHT, MAP_WIDTH, color_dark_wall, color_light_wall,color_dark_ground, color_light_ground


	#the list of objects with just the player
	objects = [player]

	if dungeon_level == 1:
		#use custom map from samples
		maps.hubmap
		color_dark_wall = libtcod.Color(50, 50, 50)
		color_light_wall = libtcod.Color(100, 100, 100)
		color_dark_ground = libtcod.Color(22, 22, 22)
		color_light_ground = libtcod.Color(42, 42, 42)

		#NOTE: height and width should really be lower-cased, since we are not treating them as constants anymore
		MAP_HEIGHT = len(maps.hubmap)
		MAP_WIDTH = len(maps.hubmap[0])

		#declare variable 'map' and fill it with blocked tilesc
		map = [[Tile(True, sludge=False, bar=False, door=False, space=False) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				if maps.hubmap[y][x] == ' ':
					map[x][y] = Tile(False, False, False, False, False)

				elif maps.hubmap[y][x] == '~':
					map[x][y] = Tile(False, True, False, False, False)
					libtcod.console_set_char(con,x,y,172)

				elif maps.hubmap[y][x] == '_':
					map[x][y] = Tile(False, False, True, False, False)

				elif maps.hubmap[y][x] == 'X':
					map[x][y] = Tile(False, False, False, True, False)

				elif maps.hubmap[y][x] == 'W':
					map[x][y] = Tile(False, False, False, False, True)
					libtcod.console_set_char(con,x,y,171)




		#upstairs = Object(2, 3, '>', 'upstairs', libtcod.white, always_visible=True)
		#objects.append(upstairs)
		#upstairs.x, upstairs.y = random_unblocked_tile_on_map()
		#upstairs.send_to_back()  #so it's drawn below the monsters

		stairs = Object(20, 5, '<', 'stairs', libtcod.white, always_visible=True)
		objects.append(stairs)
		#stairs.x, stairs.y = random_unblocked_tile_on_map()
		stairs.send_to_back()  #so it's drawn below the monsters


	else:
	#fill map with "blocked" tiles
		color_dark_wall = libtcod.Color(0, 0, 10)
		color_light_wall = libtcod.Color(50, 50, 50)
		color_dark_ground = libtcod.Color(0, 0, 0)
		color_light_ground = libtcod.Color(22, 22, 22)

		map = [[Tile(True, False, False, False, False)
				for y in range(MAP_HEIGHT)]
			   for x in range(MAP_WIDTH)]

		rooms = []
		num_rooms = 0

		for r in range(MAX_ROOMS):
			#random width and height
			w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
			h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
			#random position without going out of the boundaries of the map
			x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
			y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

			#"Rect" class makes rectangles easier to work with
			new_room = Rect(x, y, w, h)

			#run through the other rooms and see if they intersect with this one
			failed = False
			for other_room in rooms:
				if new_room.intersect(other_room):
					failed = True
					break

			if not failed:
				#this means there are no intersections, so this room is valid

				#"paint" it to the map's tiles8
				roomchoice = [create_circular_room(new_room), create_room(new_room)]
				random.choice(roomchoice)
				create_circular_room(new_room)
				create_boundaries()

				#add some contents to this room
				place_objects(new_room)

				#add furniture
				#place_furniture(new_room)

				#add monsters
				place_monsters(new_room)

				#center coordinates of new room, will be useful later
				(new_x, new_y) = new_room.center()

				if num_rooms == 0:
					#this is the first room, where the player starts at
					player.x = new_x
					player.y = new_y
				else:
					#all rooms after the first:
					#connect it to the previous room with a tunnel

					#center coordinates of previous room
					(prev_x, prev_y) = rooms[num_rooms - 1].center()

					#draw a coin (random number that is either 0 or 1)
					if libtcod.random_get_int(0, 0, 1) == 1:
						#first move horizontally, then vertically
						create_h_tunnel(prev_x, new_x, prev_y)
						create_v_tunnel(prev_y, new_y, new_x)
					else:
						#first move vertically, then horizontally
						create_v_tunnel(prev_y, new_y, prev_x)
						create_h_tunnel(prev_x, new_x, new_y)

				#finally, append the new room to the list
				rooms.append(new_room)
				num_rooms += 1

		stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
		objects.append(stairs)
		stairs.send_to_back()  #so it's drawn below the monsters

		upstairs = Object(2, 3, '>', 'upstairs', libtcod.white, always_visible=True)
		objects.append(upstairs)
		#upstairs.x, u
		# pstairs.y = random_unblocked_tile_on_map()
		upstairs.send_to_back()  #so it's drawn below the monsters

def hub():
	#Shops
	furniture_component = Furniture(use_function=Ermashopsell)
	furniture = Object(8, 2, '$', worldgen.corptwo + 'Shopping Terminal', libtcod.red, desc=worldgen.corptwo + ' Shopping Terminal', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=Vorishopsell)
	furniture = Object(9, 12, '$', worldgen.corpone + 'Shopping Terminal', libtcod.dark_red, desc=worldgen.corpone + 'Vorikov Shopping Terminal', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=foodshop)
	furniture = Object(25, 7, '$', 'Noodle Bar Terminal', libtcod.dark_green, desc='The terminal for a Noodle Bar', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=fenceshop)
	furniture = Object(62, 2, '$', 'Manual Jack, the fence', libtcod.black, desc='Manual Jack, the fence', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=potionshop)
	furniture = Object(27, 24, '$', 'Sandii, the pusher', libtcod.magenta, desc='Sandii, the pusher', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	#NPCs
	#NPC direct placement:
	#npcplace = [(4,24), (5,24), (7, 4), (9, 8), (15, 28), (30, 10)]
	#for x,y in npcplace:
	#	libtcod.namegen_parse('npcattrib.txt')
	#	name = libtcod.namegen_generate('npcnames')
	#	clothes = libtcod.namegen_generate('clothes')
	#	features = libtcod.namegen_generate('features')
	#	libtcod.namegen_parse('colours.txt')
	#	colours = libtcod.namegen_generate('colours')
	#	nonplayerchar_component = NonplayerChar(my_path=0, lastx=0, lasty=0, setx=0, sety=0, destset=False, hp=20, defense=10, strength=4, hack=0, dexterity=10, perception=4,
	#										eloyalty=0, vloyalty=0, xp=0, move_speed=5, flicker=0, robot=False, death_function=monster_death, creddrop=0, use_function=convo)
	#	ai_component = BasicNpc()
	#	npc = Object(x, y, 'N', name, libtcod.fuchsia, desc= name + "." + " They are " + features + ' and wearing a ' + colours + ' ' + clothes,
	#							 blocks=True, nonplayerchar=nonplayerchar_component, ai=ai_component)
	#	objects.append(npc)

	for n in range(1,30):
		libtcod.namegen_parse('npcattrib.txt')
		name = libtcod.namegen_generate('npcnames')
		clothes = libtcod.namegen_generate('clothes')
		features = libtcod.namegen_generate('features')
		libtcod.namegen_parse('colours.txt')
		colours = libtcod.namegen_generate('colours')

		nonplayerchar_component = NonplayerChar(my_path=0, lastx=0, lasty=0,  setx=0, sety=0, destset=False, hp=20, defense=10, strength=4, hack=0, dexterity=10, perception=4,
											eloyalty=0, vloyalty=0, xp=0, move_speed=5, flicker=0, robot=False, death_function=monster_death, creddrop=0, use_function=convo)
		ai_component = BasicNpc()
		(x,y) = random_unblocked_tile_on_map()
		npc = Object(x, y, 'N', name, libtcod.fuchsia, desc= name + "." + " They are " + features + ' and wearing a ' + colours + ' ' + clothes,
								 blocks=True, nonplayerchar=nonplayerchar_component, ai=ai_component)
		objects.append(npc)

	#n = range(1,15)
	for n in range(1,15):
		furniture_component = Furniture(use_function=rubble)
		furniture = Object(5, 5, 'x', 'rubble', libtcod.grey, desc='the cast offs of a broken city', blocks=True, furniture=furniture_component)
		furniture.x, furniture.y = random_unblocked_tile_on_map()
		objects.append(furniture)
		furniture.send_to_front()
		n+=1

	#misc
	furniture_component = Furniture(use_function=playerdoor)
	furniture = Object(61, 22, 129, 'door', libtcod.dark_flame, desc='a door', blocks=True, always_visible=True, furniture=furniture_component)
	furniture.blocks_sight = True
	objects.append(furniture)


	furniture_component = Furniture(use_function=playerterminal)
	furniture = Object(60, 21, '&', 'Player Terminal', libtcod.white, desc='Your Terminal', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=bed)
	furniture = Object(56, 21, 233, 'Bed', libtcod.lightest_amber, desc='Your Bed', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	#chairs, useless, useless chairs.
	chairplace = [(3,21),(4,21), (7,21), (8,21), (3,28),(4,28), (7,28), (8,28)]

	for x,y in chairplace:
			furniture_component = Furniture(nouse)
			furniture = Object(x, y, 'n', 'chair', libtcod.brass, desc='a chair', blocks=False, furniture=furniture_component)
			objects.append(furniture)

	#some signs

	furniture_component = Furniture(use_function=lookat)
	furniture = Object(11, 8, '?', worldgen.corptwo + ' Defence', libtcod.red, desc='Erma Corporation defence superstore', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=lookat)
	furniture = Object(11, 16, '?', worldgen.corpone + ' Surplus', libtcod.dark_red, desc='Vorikov Corporation Surplus', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=lookat)
	furniture = Object(25, 19, '?', 'Bar Artiste', libtcod.sea, desc='Bar Artiste - open all hours.', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=lookat)
	furniture = Object(61, 19, '?', 'Appartment Block Y2', libtcod.sea, desc='Appartment Block Y2', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	furniture_component = Furniture(use_function=lookat)
	furniture = Object(44, 3, '?', 'Rose Hotel', libtcod.sea, desc='The Rose Hotel', blocks=True, furniture=furniture_component)
	objects.append(furniture)
	furniture.always_visible = True

	#add the player
	player.x, player.y = 62, 22


def random_choice_index(chances):  #choose one option from list of chances, returning its index
	#the dice will land on some number between 1 and the sum of the chances
	dice = libtcod.random_get_int(0, 1, sum(chances))
 
	#go through all chances, keeping the sum so far
	running_sum = 0
	choice = 0
	for w in chances:
		running_sum += w
 
		#see if the dice landed in the part that corresponds to this choice
		if dice <= running_sum:
			return choice
		choice += 1
 
def random_choice(chances_dict):
	#choose one option from dictionary of chances, returning its key
	chances = chances_dict.values()
	strings = chances_dict.keys()
 
	return strings[random_choice_index(chances)]
 
def from_dungeon_level(table):
	#returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
	for (value, level) in reversed(table):
		if dungeon_level >= level:
			return value
	return 0

# def place_monsters(room):
#
# 	max_monsters = from_dungeon_level([[2, 1], [3, 5], [4, 8]])
# 	#chance of each monster
# 	monster_chances ={}
# 	monster_chances['thug'] = from_dungeon_level([[80, 2], [40, 5], [10,9], [0, 12]])   #thug always shows up, even if all other monsters have 0 chance
# 	monster_chances['thugboss'] = from_dungeon_level([[10, 3], [15, 5], [10, 7], [0,12]])
#
# 	monster_chances['mutant'] = from_dungeon_level([[15, 4], [30, 6], [40, 9]])
# 	monster_chances['fastmutant'] = from_dungeon_level([[5, 5], [10, 8], [20, 11]])
# 	monster_chances['dog'] = from_dungeon_level([[80, 2], [0, 3]])
# 	##robots:
# 	monster_chances['manhack'] = from_dungeon_level([[20, 4], [25, 6], [30, 8]])
# 	monster_chances['vturret'] = from_dungeon_level([[15, 5], [30, 7]])
# 	monster_chances['replicant'] = from_dungeon_level([[5, 5], [10, 7], [20, 9]])
#
#
# 	#choose random number of monsters
# 	num_monsters = libtcod.random_get_int(0, 0, max_monsters)
#
# 	for i in range(num_monsters):
# 		#choose random spot for this monster
# 		x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
# 		y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)
#
# 		#only place it if the tile is not blocked
# 		if not is_blocked(x, y):
# 			choice = random_choice(monster_chances)
# 			tmpData = monster_data[choice]
# 			fighter_component = Fighter(my_path=0, lastx=0, lasty=0, hp=tmpData['hp'], defense=tmpData['defense'], strength=tmpData['strength'], dexterity=tmpData['dexterity'],
# 										perception=tmpData['perception'], firearmdmg=tmpData['firearmdmg'], intelligence=tmpData['intelligence'], firearmacc=tmpData['firearmacc'], eloyalty=0, vloyalty=0, ammo=tmpData['ammo'],
# 										charge=0, xp=tmpData['xp'], move_speed=tmpData['move_speed'], flicker=0, robot=tmpData['robot'], death_function=tmpData['death_function'], creddrop=tmpData['creddrop'])
# 			ai_component = BasicMonster()
# 			monster = Object(x, y, tmpData['character'], tmpData['name'], tmpData['character_color'], tmpData['desc'], blocks=True, fighter=fighter_component, ai=ai_component)
# 			objects.append(monster)
def place_monsters(room):
	max_monsters = from_dungeon_level([[2, 1], [3, 5], [4, 8]])
	#chance of each monster
	monster_chances ={}
	monster_chances['Mutant'] = from_dungeon_level([[80, 2], [40, 5], [10,9], [0, 12]])   #thug always shows up, even if all other monsters have 0 chance
	monster_chances['Abomination'] = from_dungeon_level([[10, 3], [15, 5], [10, 7], [0,12]])

	#choose random number of monsters
	num_monsters = libtcod.random_get_int(0, 0, max_monsters)

	for i in range(num_monsters):
		#choose random spot for this monster
		x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
		y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

		#only place it if the tile is not blocked
		if not is_blocked(x, y):
			choice = random_choice(monster_chances)
			tmpData = monster_data[choice]
			fighter_component = Fighter(my_path=0, lastx=0, lasty=0,  hp=tmpData['hp'], defense=tmpData['defense'], power=tmpData['power'], xp=tmpData['xp'], flicker=0, death_function=tmpData['death_function'])
			ai_component = BasicMonster()
			monster = Object(x, y, tmpData['character'], tmpData['name'], tmpData['character_color'], tmpData['desc'], blocks=True, fighter=fighter_component, ai=ai_component)
			objects.append(monster)

def place_objects(room):
	#this is where we decide the chance of each monster or item appearing.
 
	#maximum number of monsters per room
	max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
 
	#chance of each monster
 
	#maximum number of items per room
	max_items = from_dungeon_level([[1, 1], [2, 4]])
 
	#chance of each item (by default they have a chance of 0 at level 1, which then goes up)
	item_chances = {}
	item_chances['heal'] = 35  #healing potion always shows up, even if all other items have 0 chance
	item_chances['lightning'] = from_dungeon_level([[25, 4]])
	item_chances['fireball'] =  from_dungeon_level([[25, 6]])
	item_chances['confuse'] =   from_dungeon_level([[10, 2]])
	item_chances['sword'] =     from_dungeon_level([[5, 4]])
	item_chances['shield'] =    from_dungeon_level([[15, 8]])
 
	#choose random number of items
	num_items = libtcod.random_get_int(0, 0, max_items)
 
	for i in range(num_items):
		#choose random spot for this item
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
		#only place it if the tile is not blocked
		if not is_blocked(x, y):
			choice = random_choice(item_chances)
			if choice == 'heal':
				#create a healing potion
				item_component = Item(use_function=cast_heal)
				item = Object(x, y, '!', 'healing potiony', libtcod.violet, item=item_component)
 
			elif choice == 'lightning':
				#create a lightning bolt scroll
				item_component = Item(use_function=cast_lightning)
				item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)
 
			elif choice == 'fireball':
				#create a fireball scroll
				item_component = Item(use_function=cast_fireball)
				item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component)
 
			elif choice == 'confuse':
				#create a confuse scroll
				item_component = Item(use_function=cast_confuse)
				item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)
 
			elif choice == 'sword':
				#create a sword
				equipment_component = Equipment(slot='right hand', power_bonus=3)
				item = Object(x, y, '/', 'sword', libtcod.sky, equipment=equipment_component)
 
			elif choice == 'shield':
				#create a shield
				equipment_component = Equipment(slot='left hand', defense_bonus=1)
				item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
 
			objects.append(item)
			item.send_to_back()  #items appear below other objects
			item.always_visible = True  #items are visible even out-of-FOV, if in an explored area
 
 
def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
	#render a bar (HP, experience, etc). first calculate the width of the bar
	bar_width = int(float(value) / maximum * total_width)

	#render the background first
	libtcod.console_set_default_background(sidebar, back_color)
	libtcod.console_rect(sidebar, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

	#now render the bar on top
	libtcod.console_set_default_background(sidebar, bar_color)
	if bar_width > 0:
		libtcod.console_rect(sidebar, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

	#finally, some centered text with the values
	libtcod.console_set_default_foreground(sidebar, libtcod.white)
	libtcod.console_print_ex(sidebar, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
							 name + ':' + str(value) + '/' + str(maximum))
 
def get_names_under_mouse():
	global mouse
	#return a string with the names of all objects under the mouse
 
	(x, y) = (mouse.cx, mouse.cy)
 
	#create a list with the names of all objects at the mouse's coordinates and in FOV
	names = [obj.name for obj in objects
			 if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
 
	names = ', '.join(names)  #join the names, separated by commas
	return names.capitalize()

def flicker_all():
	global fov_recompute
	render_all()
	timer = 0
	while (timer < 3):
		for frame in range(5):
			for object in objects:
				if object.fighter and libtcod.map_is_in_fov(fov_map, object.x, object.y) and object.fighter.flicker is not None:
					#if object.fighter.robot:
					#	libtcod.console_set_char_foreground(con, object.x, object.y, libtcod.light_blue)
					#	libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)
					#else:
					libtcod.console_set_char_foreground(con, object.x, object.y, libtcod.dark_red)
					libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)
		libtcod.console_check_for_keypress()
		#render_all()
		libtcod.console_flush()#show result
		timer += 1
	fov_recompute = True
	render_all()
	for object in objects:
		if object.fighter:
			object.fighter.flicker = None

def render_all():
	global fov_map, color_dark_wall, color_light_wall
	global color_dark_ground, color_light_ground
	global fov_recompute, hour, day, amorpm, playername, inventory, dungeon_name
	#plyx = player.x + 2
	#plyy = player.y + 2
	move_camera(player.x, player.y)
	#floordirt = 12;
	#noise2d = libtcod.noise_new(2,h=libtcod.NOISE_DEFAULT_HURST,l=libtcod.NOISE_DEFAULT_LACUNARITY,random=0)

	if fov_recompute:
		#recompute FOV if needed (the player moved or something)
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
		libtcod.console_clear(con)

		#go through all tiles, and set their background color according to the FOV
		for y in range(CAMERA_HEIGHT):
			for x in range(CAMERA_WIDTH):
				(map_x, map_y) = (camera_x + x, camera_y + y)
				visible = libtcod.map_is_in_fov(fov_map, map_x, map_y)

				wall = map[map_x][map_y].block_sight
				sludge = map[map_x][map_y].sludge
				water = map[map_x][map_y].space

				if not visible:
					#if it's not visible right now, the player can only see it if it's explored
					if map[map_x][map_y].explored:
						if wall:
							libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
						elif sludge:
							libtcod.console_set_char_background(con, x, y, libtcod.darkest_lime, libtcod.BKGND_SET)

						elif water:
							libtcod.console_set_char_background(con, x, y, libtcod.darkest_blue, libtcod.BKGND_SET)
							libtcod.console_set_char(con,x,y,171)
						else:
							libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)

				else:
					#it's visible
					if wall:
						libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
					elif sludge:
						libtcod.console_set_char_background(con, x, y, libtcod.darkest_lime, libtcod.BKGND_SET)
						libtcod.console_set_char(con,x,y,172)
					elif water:
						libtcod.console_set_char_background(con, x, y, libtcod.darkest_blue, libtcod.BKGND_SET)
						libtcod.console_set_char(con,x,y,171)
					else:
						libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)


						#since it's visible, explore it
					map[map_x][map_y].explored = True



	#draw all objects in the list, except the player. we want it to
	#always appear over all other objects! so it's drawn later.
	for object in objects:
		if object != player:
			object.draw()
	player.draw()



	#prepare to render the GUI panel
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	libtcod.console_print_frame(panel, 0, 0, 43, PANEL_HEIGHT, clear=False, flag=libtcod.BKGND_ADD, fmt=0)



	#print the game messages, one line at a time
	y = 1
	x = 1
	for (line, color) in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, x, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1

	#show the player's stats

	libtcod.console_set_default_background(sidebar, libtcod.black)
	libtcod.console_clear(sidebar)
	libtcod.console_print_frame(sidebar,0, 0, SIDEBAR_WIDTH,SIDEBAR_HEIGHT, clear=False, flag=libtcod.BKGND_ADD, fmt=0)

	#for line in range(3,33):
	#libtcod.console_print_ex(sidebar, 1, 1, libtcod.BKGND_NONE, libtcod.LEFT, str(playername))

	render_bar(1, 2, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
			   libtcod.light_red, libtcod.darker_red)

	#render_bar(1, 3, BAR_WIDTH, 'Charge', player.fighter.charge, player.fighter.base_charge,
	#		   libtcod.light_blue, libtcod.darker_blue)

	libtcod.console_print_ex(sidebar, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT,  str(dungeon_name))
	#
	# libtcod.console_print_ex(sidebar, 1, 5, libtcod.BKGND_NONE, libtcod.LEFT, 'Hunger:' + str(hunger_stat))
	# libtcod.console_print_ex(sidebar, 1, 8, libtcod.BKGND_NONE, libtcod.LEFT, 'Cr:' + str(cred))
	#
	#
	# libtcod.console_print_ex(sidebar, 1, 7, libtcod.BKGND_NONE, libtcod.LEFT, 'Day:' + str(day) + ' ' + 'Time:' + str(hour)  + str(amorpm))
	# libtcod.console_print_ex(sidebar, 1, 10, libtcod.BKGND_NONE, libtcod.LEFT, 'Ammo:' + str(player.fighter.ammo))
	#
	#
	# libtcod.console_print_ex(sidebar, 1, 22, libtcod.BKGND_NONE, libtcod.LEFT, 'Skills:')
	# libtcod.console_set_default_foreground(sidebar, libtcod.dark_green)
	# libtcod.console_print_frame(sidebar, 0, 23, SIDEBAR_WIDTH, 4, clear=False,flag=libtcod.BKGND_DEFAULT, fmt=0)
	# libtcod.console_print_ex(sidebar, 1, 24, libtcod.BKGND_NONE, libtcod.LEFT, 'Atk:' + str(player.fighter.strength))
	# libtcod.console_print_ex(sidebar, 9, 24, libtcod.BKGND_NONE, libtcod.LEFT, 'Dex:' + str(player.fighter.dexterity))
	# libtcod.console_print_ex(sidebar, 1, 25, libtcod.BKGND_NONE, libtcod.LEFT, 'Def:' + str(player.fighter.defense))
	# libtcod.console_print_ex(sidebar, 9, 25, libtcod.BKGND_NONE, libtcod.LEFT, 'Acc:' + str(player.fighter.perception))
	#
	# libtcod.console_set_default_foreground(sidebar, libtcod.white)
	# libtcod.console_print_ex(sidebar, 1, 28, libtcod.BKGND_NONE, libtcod.LEFT, 'Deck:')
	# libtcod.console_set_default_foreground(sidebar, libtcod.dark_green)
	# libtcod.console_print_frame(sidebar, 0, 29,SIDEBAR_WIDTH, 6, clear=False, flag=libtcod.BKGND_DEFAULT, fmt=0)
	# libtcod.console_print_ex(sidebar, 1, 30, libtcod.BKGND_NONE, libtcod.LEFT, '1:' + str(get_equipped_in_slot('Insert 1')))
	# libtcod.console_print_ex(sidebar, 1, 31, libtcod.BKGND_NONE, libtcod.LEFT, '2:' + str(get_equipped_in_slot('Left hand')))
	# libtcod.console_print_ex(sidebar, 1, 32, libtcod.BKGND_NONE, libtcod.LEFT, '3:' + str(get_equipped_in_slot('Right Hand')))
	# libtcod.console_print_ex(sidebar, 1, 33, libtcod.BKGND_NONE, libtcod.LEFT, '4:' + str(get_equipped_in_slot('Right Hand')))
	libtcod.console_set_default_foreground(sidebar, libtcod.light_grey)


	#display names of objects under the mouse
	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

	#blit the contents of "panel" to the root console
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y, 0.94, 0.2)
	libtcod.console_blit(sidebar, 0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT, 0,SIDEBAR_X, SIDEBAR_Y, 0.94, 0.2)



#blit the contents of "con" to the root console
	libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0, 1, 1)
 
 
def message(new_msg, color = libtcod.white):
	#split the message if necessary, among multiple lines
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
 
	for line in new_msg_lines:
		#if the buffer is full, remove the first line to make room for the new one
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]
 
		#add the new line as a tuple, with the text and the color
		game_msgs.append( (line, color) )

 
def player_move_or_attack(dx, dy):
	global fov_recompute
 
	#the coordinates the player is moving to/attacking
	x = player.x + dx
	y = player.y + dy
 
	#try to find an attackable object there
	target = None
	for object in objects:
		if object.fighter and object.x == x and object.y == y:
			target = object
			break
 
	#attack if target found, move otherwise
	if target is not None:
		player.fighter.attack(target)
	else:
		player.move(dx, dy)
		fov_recompute = True
 
def msgbox(text, width=50):
	menu(text, [], width)  #use menu() as a sort of "message box"

def menu(header, options, width):
	global acamera_x, camera_y
	if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')

	#calculate total height for the header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
	if header == '':
		header_height = 0
	height = len(options) + header_height

	#create an off-screen console that represents the menu's window
	window = libtcod.console_new(width, height+6)
	libtcod.console_set_alignment(window, libtcod.RIGHT)

	#print the header, with auto-wrap
	libtcod.console_set_default_foreground(window, libtcod.green)
	libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_ADD, libtcod.LEFT, header)

	#print all the options
	y = header_height
	letter_index = ord('a')
	for option_text in options:
		text = '(' + chr(letter_index) + ') ' + option_text
		libtcod.console_print_ex(window, 0, y, libtcod.BKGND_ADD, libtcod.LEFT, text)
		y += 1
		letter_index += 1

	#blit the contents of "window" to the root console
	x = SCREEN_WIDTH / 2 - width / 2
	y = SCREEN_HEIGHT / 2 - height / 2
	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)


	#present the root console to the player and wait for a key-press
	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)
	key = libtcod.console_wait_for_keypress(True)

	if key.vk == libtcod.KEY_ENTER and key.lalt:  #(special case) Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen)

	#convert the ASCII code to an index; if it corresponds to an option, return it
	index = key.c - ord('a')
	if index >= 0 and index < len(options): return index
	return None
 
def inventory_menu(header):
	#show a menu with each item of the inventory as an option
	if len(inventory) == 0:
		options = ['Inventory is empty.']
	else:
		options = []
		for item in inventory:
			text = item.name
			#show additional information, in case it's equipped
			if item.equipment and item.equipment.is_equipped:
				text = text + ' (on ' + item.equipment.slot + ')'
			options.append(text)
 
	index = menu(header, options, INVENTORY_WIDTH)
 
	#if an item was chosen, return it
	if index is None or len(inventory) == 0: return None
	return inventory[index].item


 
def handle_keys():
	global key
 
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		#Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
 
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit'  #exit game
 
	if game_state == 'playing':
		#movement keys
		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			player_move_or_attack(0, -1)
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			player_move_or_attack(0, 1)
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			player_move_or_attack(-1, 0)
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			player_move_or_attack(1, 0)
		elif key.vk == libtcod.KEY_HOME or key.vk == libtcod.KEY_KP7:
			player_move_or_attack(-1, -1)
		elif key.vk == libtcod.KEY_PAGEUP or key.vk == libtcod.KEY_KP9:
			player_move_or_attack(1, -1)
		elif key.vk == libtcod.KEY_END or key.vk == libtcod.KEY_KP1:
			player_move_or_attack(-1, 1)
		elif key.vk == libtcod.KEY_PAGEDOWN or key.vk == libtcod.KEY_KP3:
			player_move_or_attack(1, 1)
		elif key.vk == libtcod.KEY_KP5:
			pass  #do nothing ie wait for the monster to come to you
		else:
			#test for other keys
			key_char = chr(key.c)
 
			if key_char == 'g':
				#pick up an item
				for object in objects:  #look for an item in the player's tile
					if object.x == player.x and object.y == player.y and object.item:
						object.item.pick_up()
						break
 
			if key_char == 'i':
				#show the inventory; if an item is selected, use it
				chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
				if chosen_item is not None:
					chosen_item.use()
 
			if key_char == 'd':
				#show the inventory; if an item is selected, drop it
				chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
				if chosen_item is not None:
					chosen_item.drop()

			if key_char == 'j':
				next_level()
 
			if key_char == 'c':
				#show character information
				level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
				msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
					   '\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
					   '\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)
 
			if key_char == '<':
				#go down stairs, if the player is on them
				if stairs.x == player.x and stairs.y == player.y:
					next_level()
 
			return 'didnt-take-turn'
 
def check_level_up():
	#see if the player's experience is enough to level-up
	level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
	if player.fighter.xp >= level_up_xp:
		#it is! level up and ask to raise some stats
		player.level += 1
		player.fighter.xp -= level_up_xp
		message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)
 
		choice = None
		while choice == None:  #keep asking until a choice is made
			choice = menu('Level up! Choose a stat to raise:\n',
						  ['Constitution (+20 HP, from ' + str(player.fighter.max_hp) + ')',
						   'Strength (+1 attack, from ' + str(player.fighter.power) + ')',
						   'Agility (+1 defense, from ' + str(player.fighter.defense) + ')'], LEVEL_SCREEN_WIDTH)
 
		if choice == 0:
			player.fighter.base_max_hp += 20
			player.fighter.hp += 20
		elif choice == 1:
			player.fighter.base_power += 1
		elif choice == 2:
			player.fighter.base_defense += 1
 
def player_death(player):
	#the game ended!
	global game_state
	message('You died!', libtcod.red)
	game_state = 'dead'
 
	#for added effect, transform the player into a corpse!
	player.char = '%'
	player.color = libtcod.dark_red
 
def monster_death(monster):
	global camera_x, camera_y
	#transform it into a nasty corpse! it doesn't block, can't be
	#attacked and doesn't move
	message('The ' + monster.name + ' is dead! You gain ' + str(monster.fighter.xp) + ' XP',
			libtcod.orange)
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name
	monster.send_to_back()
	libtcod.map_set_properties(fov_map, monster.x, monster.y, True, True)

	for y in range(1,4):
		n=random.randint(-1, 2)
		if n == 1:
			bloodcolour = libtcod.dark_red
		elif n == 2:
			bloodcolour = libtcod.darker_red
		else:
			bloodcolour = libtcod.darkest_red
		(x,y) = to_camera_coordinates(monster.x,monster.y)
		libtcod.console_set_char_background(con, x, y-1, bloodcolour)
		libtcod.console_set_char_background(con, x +1, y, bloodcolour)
		y += 1

def target_tile(max_range=None):
	global key, mouse
	#return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
	while True:
		#render the screen. this erases the inventory and shows the names of objects under the mouse.
		libtcod.console_flush()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
		render_all()
 
		(x, y) = (mouse.cx, mouse.cy)
 
		if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
			return (None, None)  #cancel if the player right-clicked or pressed Escape
 
		#accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
		if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
				(max_range is None or player.distance(x, y) <= max_range)):
			return (x, y)
 
def target_monster(max_range=None):
	#returns a clicked monster inside FOV up to a range, or None if right-clicked
	while True:
		(x, y) = target_tile(max_range)
		if x is None:  #player cancelled
			return None
 
		#return the first clicked monster, otherwise continue looping
		for obj in objects:
			if obj.x == x and obj.y == y and obj.fighter and obj != player:
				return obj
 
def closest_monster(max_range):
	#find closest enemy, up to a maximum range, and in the player's FOV
	closest_enemy = None
	closest_dist = max_range + 1  #start with (slightly more than) maximum range
 
	for object in objects:
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
			#calculate distance between this object and the player
			dist = player.distance_to(object)
			if dist < closest_dist:  #it's closer, so remember it
				closest_enemy = object
				closest_dist = dist
	return closest_enemy
 
def cast_heal():
	#heal the player
	if player.fighter.hp == player.fighter.max_hp:
		message('You are already at full health.', libtcod.red)
		return 'cancelled'
 
	message('Your wounds start to feel better!', libtcod.light_violet)
	player.fighter.heal(HEAL_AMOUNT)
 
def cast_lightning():
	#find closest enemy (inside a maximum range) and damage it
	monster = closest_monster(LIGHTNING_RANGE)
	if monster is None:  #no enemy found within maximum range
		message('No enemy is close enough to strike.', libtcod.red)
		return 'cancelled'
 
	#zap it!
	message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
			+ str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
	monster.fighter.take_damage(LIGHTNING_DAMAGE)
 
def cast_fireball():
	#ask the player for a target tile to throw a fireball at
	message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
	(x, y) = target_tile()
	if x is None: return 'cancelled'
	message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
 
	for obj in objects:  #damage every fighter in range, including the player
		if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
			message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
			obj.fighter.take_damage(FIREBALL_DAMAGE)
 
def cast_confuse():
	#ask the player for a target to confuse
	message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
	monster = target_monster(CONFUSE_RANGE)
	if monster is None: return 'cancelled'
 
	#replace the monster's AI with a "confused" one; after some turns it will restore the old AI
	old_ai = monster.ai
	monster.ai = ConfusedMonster(old_ai)
	monster.ai.owner = monster  #tell the new component who owns it
	message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)
 
 
def save_game():
	#open a new empty shelve (possibly overwriting an old one) to write the game data
	file = shelve.open('savegame', 'n')
	file['map'] = map
	file['objects'] = objects
	file['player_index'] = objects.index(player)  #index of player in objects list
	file['stairs_index'] = objects.index(stairs)  #same for the stairs
	file['inventory'] = inventory
	file['game_msgs'] = game_msgs
	file['game_state'] = game_state
	file['dungeon_level'] = dungeon_level
	file.close()
 
def load_game():
	#open the previously saved shelve and load the game data
	global map, objects, player, stairs, inventory, game_msgs, game_state, dungeon_level
 
	file = shelve.open('savegame', 'r')
	map = file['map']
	objects = file['objects']
	player = objects[file['player_index']]  #get index of player in objects list and access it
	stairs = objects[file['stairs_index']]  #same for the stairs
	inventory = file['inventory']
	game_msgs = file['game_msgs']
	game_state = file['game_state']
	dungeon_level = file['dungeon_level']
	file.close()
 
	initialize_fov()
 
def new_game():
	global player, inventory, game_msgs, game_state, dungeon_level, dungeon_name
	#create object representing the player
	fighter_component = Fighter(my_path=0, lastx=0, lasty=0,hp=100, defense=1, power=2, xp=0, flicker=0, death_function=player_death)
	player = Object(20, 12, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)
 
	player.level = 1
 
	#generate map (at this point it's not drawn to the screen)
	dungeon_level = 1
	dungeon_name = "hello"
	make_map()
	initialize_fov()
 
	game_state = 'playing'
	inventory = []
 
	#create the list of game messages and their colors, starts empty
	game_msgs = []
 
	#a warm welcoming message!
	message('You awaken on a ship floating in space. It seems to be docked to something, and you notice the warning lights on the resource gauges are on.', libtcod.red)
 
	#initial equipment: a dagger
	equipment_component = Equipment(slot='right hand', power_bonus=2)
	obj = Object(0, 0, '-', 'a dagger', libtcod.sky, equipment=equipment_component)
	inventory.append(obj)
	equipment_component.equip()
	obj.always_visible = True
 
def next_level():
	#advance to the next level
	global dungeon_level, dungeon_name, player
	global color_dark_wall, color_light_wall, color_dark_ground, color_light_ground
	if dungeon_level == 1:
		file = shelve.open('hub', 'n')
		file['map'] = map
		file['objects'] = objects
		file['player_index'] = objects.index(player)
		file['stairs_index'] = objects.index(stairs)  #same for the stairs
		#file['upstairs_index'] = objects.index(upstairs)
		file.close()

		color_dark_wall = libtcod.Color(22, 22, 22)
		color_light_wall = libtcod.Color(54, 54, 54)
		color_dark_ground = libtcod.Color(48, 38, 38)
		color_light_ground = libtcod.Color(86, 76, 76)

		libtcod.namegen_parse('shipnames.txt')
		shipname = libtcod.namegen_generate('shipnames')

		dungeon_level += 1
		dungeon_name = shipname
		make_map()  #create a fresh new level!
		initialize_fov()
	else:
		dungeon_level += 1
		message('You descend deeper into the ship', libtcod.red)
		make_map()  #create a fresh new level!
		initialize_fov()

def past_level():
	#advance to the next level
	global dungeon_level, map, objects, player, stairs, upstairs, inventory, game_msgs, game_state, dungeon_level
	global color_dark_wall, color_light_wall, color_dark_ground, color_light_ground

	dungeon_level -= 1
	if dungeon_level == 1:
		file = shelve.open('hub', 'r')
		map = file['map']
		objects = file['objects']
		player = objects[file['player_index']]
		stairs = objects[file['stairs_index']]  #same for the stairs
		#upstairs = objects[file['upstairs_index']]
		file.close()

		message('You climb through the airlock back into the ship')
		initialize_fov()


	else:
		message('You climb upwards...', libtcod.red)
		make_map()  #create a fresh new level!
		initialize_fov()

def load_data():
	parser = libtcod.parser_new()
	# load monster data
	monsterStruct = libtcod.parser_new_struct(parser, 'monster')
	libtcod.struct_add_property(monsterStruct, 'name', libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(monsterStruct, 'character', libtcod.TYPE_CHAR, True)
	libtcod.struct_add_property(monsterStruct, 'character_color', libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(monsterStruct, 'desc', libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(monsterStruct, 'hp', libtcod.TYPE_INT, True)
	libtcod.struct_add_property(monsterStruct, 'defense', libtcod.TYPE_INT, True)
	libtcod.struct_add_property(monsterStruct, 'power', libtcod.TYPE_INT, True)
	libtcod.struct_add_property(monsterStruct, 'xp', libtcod.TYPE_INT, True)
	libtcod.struct_add_property(monsterStruct, 'death_function', libtcod.TYPE_STRING, True)
	libtcod.parser_run(parser, os.path.join('data', 'monster_data.cfg'), MonsterDataListener())

	libtcod.parser_delete(parser)

def initialize_fov():
	global fov_recompute, fov_map
	fov_recompute = True
 
	#create the FOV map, according to the generated map
	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
 
	libtcod.console_clear(con)  #unexplored areas start black (which is the default background color)
 
def play_game():
	global key, mouse, camera_x, camera_y

	player_action = None

	mouse = libtcod.Mouse()
	key = libtcod.Key()
	(camera_x, camera_y) = (0, 0)

	#main loop
	while not libtcod.console_is_window_closed():
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
		#render the screen
		render_all()
 
		libtcod.console_flush()
 
		#level up if needed
		check_level_up()
 
		#erase all objects at their old locations, before they move
		#erase all objects at their old locations, before they move
		for object in objects:
			if object.fighter:
				if object.fighter.flicker is not None:
					flicker_all()
			for object in objects:
				object.clear()
		for object in objects:
			object.clear()
 
		#handle keys and exit game if needed
		player_action = handle_keys()
		if player_action == 'exit':
			save_game()
			break
 
		#let monsters take their turn
		if game_state == 'playing' and player_action != 'didnt-take-turn':
			for object in objects:
				if object.ai:
					object.ai.take_turn()
 
def main_menu():

	img = libtcod.image_load('image.png')
 
	while not libtcod.console_is_window_closed():
		#show the background image, at twice the regular console resolution
		libtcod.image_blit_2x(img, 0, 0, 0, 0,0, w=-1, h=-1)
 
		#show the game's title, and some credits!
		libtcod.console_set_default_foreground(0, libtcod.light_yellow)
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
								 'A Scream in Space')
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER, 'By Hoim')
 
		#show options and wait for the player's choice
		choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
 
		if choice == 0:  #new game
			new_game()
			play_game()
		if choice == 1:  #load last game
			try:
				load_game()
			except:
				msgbox('\n No saved game to load.\n', 24)
				continue
			play_game()
		elif choice == 2:  #quit
			break

libtcod.console_set_custom_font('dejavu12x12.png', libtcod.FONT_TYPE_GRAYSCALE | libtcod.FONT_LAYOUT_TCOD)
#libtcod.console_set_custom_font('Bisasam20x20.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_ASCII_INROW)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'A Scream in Space', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

sidebar = libtcod.console_new(SIDEBAR_WIDTH, SCREEN_HEIGHT)
monster_data = {}
load_data()
main_menu()