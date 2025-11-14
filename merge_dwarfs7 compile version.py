import pygame
import sys
import random
import copy # Needed for deep copying the game map
import math # For distance calculation
import os # NEW: Import the os module

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Not running in a PyInstaller bundle
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)

# --- Initialization ---
pygame.init()
pygame.font.init() # Initialize the font module
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.mixer.set_num_channels(16) # NEW: Allow for 16 simultaneous sounds

# --- NEW: Camera & Window Constants ---
# The Window is the fixed-size application window
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 960 # 900 for game + 60 for UI

# Base Map size (Level 1)
BASE_MAP_WIDTH = 60
BASE_MAP_HEIGHT = 45

# --- Constants ---
TILE_SIZE = 20 # This is the *base* pixel size of one tile at 1.0 zoom
UI_BAR_HEIGHT = 60

# Tile Types (using numbers to represent them)
TILE_DIRT = 0
TILE_EMPTY = 1
TILE_GOLD = 2
TILE_PRESENT = 3
TILE_CHEST = 4
TILE_WATER = 5
TILE_LAVA = 6
TILE_WALL = 7
TILE_UPGRADE_LOOT = 8  # NEW: Star (Mass Upgrade)
TILE_DWARF_LOOT = 9    # NEW: Heart (L1 Spawn)
TILE_WATER_SOURCE = 10
TILE_LAVA_SOURCE = 11
TILE_HARD_DIRT = 12
TILE_CRACKED_DIRT = 13
# NEW: Tool Sprites (Not placed on map, just for loading)
TILE_GOGGLES = 14
TILE_ALE = 15
TILE_PICKAXE = 16

# Map Seeding Properties (Base values)
BASE_TOTAL_CHESTS = 10
BASE_TOTAL_WATER_POCKETS = 5
BASE_TOTAL_LAVA_POCKETS = 3
BASE_HARD_DIRT_RADIUS = 15

GOLD_CHANCE = 0.09
PRESENT_CHANCE = 0.01      # Now spawns a tool
UPGRADE_LOOT_CHANCE = 0.005 # Star (Mass Upgrade)
DWARF_LOOT_CHANCE = 0.002   # Heart (L1 Spawn)
CRACKED_DIRT_CHANCE = 0.05

# Fog of War Types
TILE_FOG_HIDDEN = 0
TILE_FOG_REVEALED = 1

# Colors (REMOVED game colors, kept UI colors)
COLOR_GRID = (40, 40, 40)
COLOR_FOG_HIDDEN = (0, 0, 0)
COLOR_UI_TEXT = (255, 255, 255)
COLOR_UI_BACKGROUND = (20, 20, 20)

# --- Arrow Properties ---
ARROW_DIRECTIONS = [
    (0, -1), # 0: Up
    (1, 0),  # 1: Right
    (0, 1),  # 2: Down
    (-1, 0)  # 3: Left
]

# --- Dwarf Properties ---
DWARF_SPEEDS = [1000, 800, 600, 400, 200] # Movement delay (in ms)
MAX_LEVEL = 5
MIN_LEVEL_FOR_HARD_DIRT = 3

DWARF_REVEAL_RADIUS = 2
DWARF_SPAWN_DELAY = 30000 # 30 seconds
DROWN_TIME = 5000 # 5 seconds

# --- UI Properties ---
UI_FONT = pygame.font.SysFont('Arial', 18)
UI_FONT_CONTROLS = pygame.font.SysFont('Arial', 14)
UI_FONT_GAMEOVER = pygame.font.SysFont('Arial', 48, bold=True)
CONTROL_TEXT_COLOR = (150, 150, 150) # Gray
GAMEOVER_TEXT_COLOR = (255, 0, 0) # Red
WIN_TEXT_COLOR = (0, 255, 0) # Green

# --- Minimap Properties ---
MINIMAP_WIDTH = 240 # 240 pixels wide
MINIMAP_HEIGHT = int(MINIMAP_WIDTH * (BASE_MAP_HEIGHT / BASE_MAP_WIDTH)) # 180 pixels
MINIMAP_X = WINDOW_WIDTH - MINIMAP_WIDTH - 10 # 10px from right edge
MINIMAP_Y = 10 # 10px from top of game area
MINIMAP_BG_COLOR = (10, 10, 10, 200) # Semi-transparent dark bg
MINIMAP_BORDER_COLOR = (100, 100, 100)
# Colors for minimap pixels
MINIMAP_COLORS = {
    TILE_DIRT: (115, 79, 45),
    TILE_HARD_DIRT: (74, 51, 29),
    TILE_CRACKED_DIRT: (160, 110, 64),
    TILE_EMPTY: (20, 20, 20),
    TILE_WALL: (100, 100, 100),
    TILE_WATER: (0, 100, 255),
    TILE_LAVA: (255, 50, 0),
    TILE_WATER_SOURCE: (0, 150, 255),
    TILE_LAVA_SOURCE: (255, 100, 0),
    TILE_GOLD: (255, 215, 0),
    TILE_CHEST: (139, 69, 19),
    TILE_PRESENT: (0, 200, 0),
    TILE_UPGRADE_LOOT: (200, 200, 255), # NEW: Star Color
    TILE_DWARF_LOOT: (255, 0, 100)  # NEW: Heart Color
}
DWARF_MINIMAP_COLOR = (255, 255, 255)

# --- Game Timers & Costs ---
FLUID_UPDATE_DELAY = 500
FLUID_LIFETIME = 3000
WALL_COST = 1
UPGRADE_COSTS = [10, 20, 30, 40, 999]
WARNING_DURATION = 3000 # 3 seconds

# --- Asset Loading ---
SPRITESHEET_FILE = 'spritesheet.png'
script_dir = os.path.dirname(__file__)
spritesheet_path = resource_path(SPRITESHEET_FILE)

sprite_library = {} # Dictionary to hold our sliced sprites
sprite_cache = {} # NEW: Holds scaled sprites for current zoom
previous_zoom_level = -1 # NEW: Used to detect zoom changes

sound_library = {} # NEW: Dictionary for loaded sounds

def play_sound(sound_name):
    """NEW: Helper function to safely play a sound."""
    if sound_name in sound_library:
        sound_library[sound_name].play()

def load_spritesheet():
    """Loads and slices the spritesheet into the sprite_library."""
    try:
        sheet = pygame.image.load(spritesheet_path).convert_alpha()
    except pygame.error as e:
        print(f"Unable to load spritesheet: {spritesheet_path}")
        print(e)
        pygame.quit()
        sys.exit()

    # --- NEW: Updated Sprite Layout based on image_c58059.png ---
    
    # Row 0 (y=0): Terrain
    sprite_library['TILE_EMPTY'] = sheet.subsurface((0*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_DIRT'] = sheet.subsurface((1*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_HARD_DIRT'] = sheet.subsurface((2*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_WALL'] = sheet.subsurface((3*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_GOLD'] = sheet.subsurface((4*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_CHEST'] = sheet.subsurface((5*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_PRESENT'] = sheet.subsurface((6*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_UPGRADE_LOOT'] = sheet.subsurface((7*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)) # Star
    sprite_library['TILE_DWARF_LOOT'] = sheet.subsurface((8*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)) # Heart
    
    # Row 1 (y=20): Fluids & Tools
    sprite_library['TILE_WATER'] = sheet.subsurface((0*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_LAVA'] = sheet.subsurface((1*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_WATER_SOURCE'] = sheet.subsurface((2*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_LAVA_SOURCE'] = sheet.subsurface((3*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['TILE_CRACKED_DIRT'] = sheet.subsurface((4*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE)) # Moved
    sprite_library['TILE_GOGGLES'] = sheet.subsurface((5*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE)) # New
    sprite_library['TILE_ALE'] = sheet.subsurface((6*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE)) # New
    sprite_library['TILE_PICKAXE'] = sheet.subsurface((7*TILE_SIZE, TILE_SIZE, TILE_SIZE, TILE_SIZE)) # New
    
    # Row 2 (y=40): Dwarves
    sprite_library['DWARF_L1'] = sheet.subsurface((0*TILE_SIZE, 2*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['DWARF_L2'] = sheet.subsurface((1*TILE_SIZE, 2*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['DWARF_L3'] = sheet.subsurface((2*TILE_SIZE, 2*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['DWARF_L4'] = sheet.subsurface((3*TILE_SIZE, 2*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['DWARF_L5'] = sheet.subsurface((4*TILE_SIZE, 2*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    
    # Row 3 (y=60): Arrows
    sprite_library['ARROW_UP'] = sheet.subsurface((0*TILE_SIZE, 3*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['ARROW_RIGHT'] = sheet.subsurface((1*TILE_SIZE, 3*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['ARROW_DOWN'] = sheet.subsurface((2*TILE_SIZE, 3*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    sprite_library['ARROW_LEFT'] = sheet.subsurface((3*TILE_SIZE, 3*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    
    print("Spritesheet loaded and sliced successfully.")

def scale_sprites(zoom):
    """NEW: Re-scales all sprites and stores them in sprite_cache."""
    global sprite_cache, previous_zoom_level
    
    current_tile_size = int(TILE_SIZE * zoom)
    if current_tile_size == previous_zoom_level:
        return # No change, cache is still valid
        
    if current_tile_size <= 0:
        sprite_cache = {} # Zoomed out too far to draw
        return

    sprite_cache = {} # Clear old cache
    for key, sprite in sprite_library.items():
        try:
            sprite_cache[key] = pygame.transform.scale(sprite, (current_tile_size, current_tile_size))
        except ValueError: # Can happen if current_tile_size is 0
            pass 
    
    previous_zoom_level = current_tile_size

def load_sounds():
    """NEW: Loads all sound files into the sound_library."""
    sound_files = {
        'music': 'music.ogg',
        'reward': 'reward.ogg',
        'death': 'death.ogg',
        'spawn': 'spawn.ogg',
        'warning': 'warning.ogg',
        'win': 'win.ogg',
        'upgrade': 'upgrade.ogg',
        'cavein': 'cavein.ogg'
    }
    
    for key, filename in sound_files.items():
        path = resource_path(filename)
        if not os.path.exists(path):
            print(f"Warning: Sound file not found: {filename}")
            continue
        
        try:
            if key == 'music':
                pygame.mixer.music.load(path)
            else:
                sound_library[key] = pygame.mixer.Sound(path)
        except pygame.error as e:
            print(f"Error loading sound {filename}: {e}")
            
    # Set volumes
    if 'reward' in sound_library: sound_library['reward'].set_volume(0.6)
    if 'spawn' in sound_library: sound_library['spawn'].set_volume(0.8)
    if 'upgrade' in sound_library: sound_library['upgrade'].set_volume(0.8)
    if 'death' in sound_library: sound_library['death'].set_volume(0.7)
    if 'warning' in sound_library: sound_library['warning'].set_volume(1.0)
    if 'win' in sound_library: sound_library['win'].set_volume(1.0)
    if 'cavein' in sound_library: sound_library['cavein'].set_volume(0.9)

    pygame.mixer.music.set_volume(0.5)

# --- NEW: Coordinate Helper Functions ---

def world_to_screen(world_x, world_y):
    """Converts game world pixel coordinates to on-screen pixel coordinates."""
    screen_x = (world_x * zoom_level) - camera_x
    screen_y = (world_y * zoom_level) - camera_y
    return int(screen_x), int(screen_y)

def screen_to_world(screen_x, screen_y):
    """Converts on-screen pixel coordinates to game world pixel coordinates."""
    world_x = (screen_x + camera_x) / zoom_level
    world_y = (screen_y + camera_y) / zoom_level
    return world_x, world_y

def world_to_grid(world_x, world_y):
    """Converts game world pixel coordinates to grid (col, row) coordinates."""
    grid_x = int(world_x / TILE_SIZE)
    grid_y = int(world_y / TILE_SIZE)
    return grid_x, grid_y

def screen_to_grid(screen_x, screen_y):
    """Converts on-screen pixel coordinates directly to grid (col, row) coordinates."""
    if screen_y < UI_BAR_HEIGHT: # Clicked in UI bar
        return -1, -1
        
    # Adjust for UI bar and camera
    world_x, world_y = screen_to_world(screen_x, screen_y - UI_BAR_HEIGHT)
    
    grid_x, grid_y = world_to_grid(world_x, world_y)
    
    # Check if click is valid
    if (0 <= grid_x < MAP_WIDTH) and (0 <= grid_y < MAP_HEIGHT):
        return grid_x, grid_y
    else:
        return -1, -1 # Clicked outside map bounds

def clamp_camera():
    """NEW: Prevents camera from panning off the edge of the world."""
    global camera_x, camera_y
    
    current_tile_size = int(TILE_SIZE * zoom_level)
    if current_tile_size <= 0: return

    # Max camera coordinates
    max_cam_x = (MAP_WIDTH * TILE_SIZE * zoom_level) - WINDOW_WIDTH
    max_cam_y = (MAP_HEIGHT * TILE_SIZE * zoom_level) - (WINDOW_HEIGHT - UI_BAR_HEIGHT)
    
    camera_x = max(0, min(camera_x, max_cam_x))
    camera_y = max(0, min(camera_y, max_cam_y))
    
    # If map is smaller than screen, just center it
    if max_cam_x < 0: camera_x = (max_cam_x) / 2
    if max_cam_y < 0: camera_y = (max_cam_y) / 2

# --- Arrow Class ---
class Arrow:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.direction_index = 0
        self.dx, self.dy = ARROW_DIRECTIONS[self.direction_index]
        self.sprite_key = 'ARROW_UP'

    def cycle_direction(self):
        self.direction_index = (self.direction_index + 1) % len(ARROW_DIRECTIONS)
        self.dx, self.dy = ARROW_DIRECTIONS[self.direction_index]
        
        if self.direction_index == 0: self.sprite_key = 'ARROW_UP'
        elif self.direction_index == 1: self.sprite_key = 'ARROW_RIGHT'
        elif self.direction_index == 2: self.sprite_key = 'ARROW_DOWN'
        elif self.direction_index == 3: self.sprite_key = 'ARROW_LEFT'

    def draw(self, surface, screen_x, screen_y, scaled_sprite):
        """NEW: Draws the arrow at a calculated screen position."""
        surface.blit(scaled_sprite, (screen_x, screen_y))


# --- Dwarf Class ---
class Dwarf:
    def __init__(self, x, y, level=1):
        self.x = x
        self.y = y
        self.level = 0
        self.alive = True
        self.dx = 0 
        self.dy = 0
        self.last_move_time = pygame.time.get_ticks()
        self.move_delay = 500
        self.base_move_delay = 500 # NEW: For pickaxe speed
        self.sprite_key = 'DWARF_L1'
        self.drown_timer_start = 0
        self.is_in_water = False
        
        # --- NEW: Tool Properties ---
        # BUGFIX: Ensured these are all False by default.
        self.has_pickaxe = False
        self.has_goggles = False
        self.has_ale = False
        
        self.set_level(level)
        self.pick_random_direction()

    def set_level(self, new_level):
        self.level = min(new_level, MAX_LEVEL)
        level_index = self.level - 1
        self.sprite_key = f'DWARF_L{self.level}'
        # NEW: Set base move delay
        self.base_move_delay = DWARF_SPEEDS[level_index]
        self.move_delay = self.base_move_delay

    def pick_random_direction(self, exclude_dir=None):
        directions = [(0, -1, 'up'), (0, 1, 'down'), (-1, 0, 'left'), (1, 0, 'right')]
        
        if exclude_dir:
            directions = [d for d in directions if (d[0], d[1]) != exclude_dir]
        
        if not directions:
            directions = [(0, -1, 'up'), (0, 1, 'down'), (-1, 0, 'left'), (1, 0, 'right')]
            
        choice = random.choice(directions)
        self.dx, self.dy = choice[0], choice[1]

    def draw(self, surface, screen_x, screen_y, scaled_sprite):
        """NEW: Draws the dwarf at a calculated screen position."""
        surface.blit(scaled_sprite, (screen_x, screen_y))
        
    def is_target_blocked(self, new_x, new_y, game_map):
        """Helper to check if a tile is passable."""
        if not (0 <= new_x < MAP_WIDTH) or not (0 <= new_y < MAP_HEIGHT):
            return True # Map boundary
            
        target_tile = game_map[new_y][new_x]
        
        if target_tile in [TILE_WALL, TILE_WATER_SOURCE, TILE_LAVA_SOURCE]:
            return True
        
        # NEW: Pickaxe check
        if target_tile == TILE_HARD_DIRT and self.level < MIN_LEVEL_FOR_HARD_DIRT and not self.has_pickaxe:
            return True
            
        return False

    def find_adjacent_reward(self, game_map, dwarf_list):
        """AI: Look for adjacent rewards and turn towards them."""
        # NEW: Updated reward tiles
        REWARD_TILES = [TILE_GOLD, TILE_PRESENT, TILE_CHEST, TILE_UPGRADE_LOOT, TILE_DWARF_LOOT]
        
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = self.x + dx, self.y + dy
            if (0 <= nx < MAP_WIDTH) and (0 <= ny < MAP_HEIGHT):
                if game_map[ny][nx] in REWARD_TILES:
                    self.dx, self.dy = dx, dy
                    return True # Found a reward
        
        for other_dwarf in dwarf_list:
            if other_dwarf is not self and other_dwarf.alive and other_dwarf.level == self.level:
                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    if self.x + dx == other_dwarf.x and self.y + dy == other_dwarf.y:
                        self.dx, self.dy = dx, dy
                        return True # Found a merge
        
        return False # No adjacent reward

    def move(self, game_map, fog_map, dwarf_list):
        new_x = self.x + self.dx
        new_y = self.y + self.dy

        if not (0 <= new_x < MAP_WIDTH) or not (0 <= new_y < MAP_HEIGHT):
            return None

        target_tile_type = game_map[new_y][new_x]
        
        if target_tile_type == TILE_LAVA:
            self.alive = False
            play_sound('death')
            return None
        
        # NEW: Pickaxe check
        if target_tile_type == TILE_HARD_DIRT and self.level < MIN_LEVEL_FOR_HARD_DIRT and not self.has_pickaxe:
            return None # Blocked
        
        if target_tile_type in [TILE_WALL, TILE_WATER_SOURCE, TILE_LAVA_SOURCE]:
            return None
        
        for other_dwarf in dwarf_list:
            if other_dwarf is not self and other_dwarf.x == new_x and other_dwarf.y == new_y:
                if other_dwarf.level != self.level:
                    return None

        self.x = new_x
        self.y = new_y
        
        # NEW: Updated reward logic
        reward = None
        if target_tile_type == TILE_GOLD:
            reward = 'gold'
        elif target_tile_type == TILE_PRESENT:
            reward = 'present' # Now gives tool
        elif target_tile_type == TILE_CHEST:
            reward = 'chest'
        elif target_tile_type == TILE_UPGRADE_LOOT:
            reward = 'upgrade_loot' # Star (Mass Upgrade)
        elif target_tile_type == TILE_DWARF_LOOT:
            reward = 'dwarf_loot' # Heart (L1 Spawn)
        elif target_tile_type == TILE_CRACKED_DIRT:
            reward = 'cracked_dirt'

        if target_tile_type != TILE_EMPTY and target_tile_type != TILE_WATER:
            game_map[self.y][self.x] = TILE_EMPTY
            
        self.reveal_surroundings(fog_map)
        
        return reward

    def check_for_arrow(self, arrow_list):
        for arrow in arrow_list:
            if self.x == arrow.x and self.y == arrow.y:
                self.dx = arrow.dx
                self.dy = arrow.dy
                return True
        return False
        
    def update(self, game_map, fog_map, arrow_list, dwarf_list, current_time):
        if not self.alive:
            return None
        
        # --- NEW: Ale (Drowning) Logic ---
        current_tile = game_map[self.y][self.x]
        if current_tile == TILE_WATER:
            if not self.is_in_water:
                self.is_in_water = True
                self.drown_timer_start = current_time
            else:
                # Check timer
                drown_limit = (DROWN_TIME * 3) if self.has_ale else DROWN_TIME
                if current_time - self.drown_timer_start > drown_limit:
                    self.alive = False
                    play_sound('death')
                    return None
        else:
            self.is_in_water = False
            self.drown_timer_start = 0
            
        reward = None
        
        # --- NEW: Pickaxe Speed Logic ---
        # Check target tile *before* moving
        current_move_delay = self.base_move_delay
        target_x, target_y = self.x + self.dx, self.y + self.dy
        if (0 <= target_x < MAP_WIDTH) and (0 <= target_y < MAP_HEIGHT):
            target_tile = game_map[target_y][target_x]
            # Fast digging for dirt
            if self.has_pickaxe and target_tile in [TILE_DIRT, TILE_CRACKED_DIRT]:
                current_move_delay = self.base_move_delay // 2
            # Normal speed for hard dirt (but still possible)
            elif self.has_pickaxe and target_tile == TILE_HARD_DIRT:
                current_move_delay = self.base_move_delay
        
        if current_time - self.last_move_time > current_move_delay: # Use dynamic speed
            
            # --- AI Logic Priority ---
            has_arrow = self.check_for_arrow(arrow_list)
            
            has_reward = False
            if not has_arrow:
                has_reward = self.find_adjacent_reward(game_map, dwarf_list)

            if not has_arrow and not has_reward:
                if self.is_target_blocked(target_x, target_y, game_map):
                    self.pick_random_direction(exclude_dir=(-self.dx, -self.dy))

            if self.dx != 0 or self.dy != 0:
                reward = self.move(game_map, fog_map, dwarf_list)
                
            self.last_move_time = current_time
            
        return reward

    def reveal_surroundings(self, fog_map):
        # NEW: Goggles check
        radius = DWARF_REVEAL_RADIUS * 2 if self.has_goggles else DWARF_REVEAL_RADIUS
        
        for r in range(-radius, radius + 1):
            for c in range(-radius, radius + 1):
                map_x = self.x + c
                map_y = self.y + r
                
                if (0 <= map_x < MAP_WIDTH) and (0 <= map_y < MAP_HEIGHT):
                    fog_map[map_y][map_x] = TILE_FOG_REVEALED

# --- Game Functions ---

def setup_level(level_number):
    """
    Generates a new level and resets all game state variables.
    """
    global game_map, fog_map, fluid_lifetime_map, arrow_list, dwarf_list
    global gold_count, chests_found, current_upgrade_level, game_over, win_state
    global last_dwarf_spawn_time, last_fluid_update_time, flood_warnings
    global MAP_WIDTH, MAP_HEIGHT, TOTAL_CHESTS, TOTAL_WATER_POCKETS, TOTAL_LAVA_POCKETS
    global SPAWN_POINT_X, SPAWN_POINT_Y, HARD_DIRT_RADIUS
    global minimap_surface, minimap_pixel_size_x, minimap_pixel_size_y

    # --- 1. Calculate new level properties ---
    level_modifier = level_number - 1
    
    MAP_WIDTH = BASE_MAP_WIDTH + (level_modifier * 10)
    MAP_HEIGHT = BASE_MAP_HEIGHT + (level_modifier * 5)
    TOTAL_CHESTS = BASE_TOTAL_CHESTS + (level_modifier * 2)
    TOTAL_WATER_POCKETS = BASE_TOTAL_WATER_POCKETS + level_modifier
    TOTAL_LAVA_POCKETS = BASE_TOTAL_LAVA_POCKETS + level_modifier
    SPAWN_POINT_X = MAP_WIDTH // 2
    SPAWN_POINT_Y = MAP_HEIGHT // 2
    HARD_DIRT_RADIUS = BASE_HARD_DIRT_RADIUS + level_modifier

    # --- 2. Create Minimap Surface & Scaling ---
    minimap_surface = pygame.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT), pygame.SRCALPHA)
    minimap_pixel_size_x = MINIMAP_WIDTH / MAP_WIDTH
    minimap_pixel_size_y = MINIMAP_HEIGHT / MAP_HEIGHT
    
    # --- 3. Generate Game Map ---
    game_map = []
    for row in range(MAP_HEIGHT):
        new_row = []
        for col in range(MAP_WIDTH):
            tile_to_add = TILE_DIRT
            if (abs(col - SPAWN_POINT_X) > 5) or (abs(row - SPAWN_POINT_Y) > 5):
                rand_val = random.random()
                # NEW: Updated chances
                if rand_val < DWARF_LOOT_CHANCE:
                    tile_to_add = TILE_DWARF_LOOT # Heart (L1 Spawn)
                elif rand_val < (DWARF_LOOT_CHANCE + UPGRADE_LOOT_CHANCE):
                    tile_to_add = TILE_UPGRADE_LOOT # Star (Mass Upgrade)
                elif rand_val < (DWARF_LOOT_CHANCE + UPGRADE_LOOT_CHANCE + PRESENT_CHANCE):
                    tile_to_add = TILE_PRESENT # Tool Box
                elif rand_val < (DWARF_LOOT_CHANCE + UPGRADE_LOOT_CHANCE + PRESENT_CHANCE + GOLD_CHANCE):
                    tile_to_add = TILE_GOLD
            new_row.append(tile_to_add)
        game_map.append(new_row)

    # --- Add Hard Dirt ---
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if game_map[y][x] == TILE_DIRT:
                distance = math.sqrt((x - SPAWN_POINT_X)**2 + (y - SPAWN_POINT_Y)**2)
                if distance > HARD_DIRT_RADIUS:
                    game_map[y][x] = TILE_HARD_DIRT
    
    # --- Add Cracked Dirt ---
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if game_map[y][x] in [TILE_DIRT, TILE_HARD_DIRT]:
                if random.random() < CRACKED_DIRT_CHANCE:
                    game_map[y][x] = TILE_CRACKED_DIRT
                    
    # --- Seed Chests ---
    chests_placed = 0
    while chests_placed < TOTAL_CHESTS:
        rand_x = random.randint(0, MAP_WIDTH - 1)
        rand_y = random.randint(0, MAP_HEIGHT - 1)
        if (game_map[rand_y][rand_x] in [TILE_HARD_DIRT, TILE_CRACKED_DIRT]):
            game_map[rand_y][rand_x] = TILE_CHEST
            chests_placed += 1

    # --- Seed Fluids ---
    seed_fluid_pockets(game_map, TOTAL_WATER_POCKETS, TILE_WATER_SOURCE)
    seed_fluid_pockets(game_map, TOTAL_LAVA_POCKETS, TILE_LAVA_SOURCE)

    # --- 4. Generate Fog Map ---
    fog_map = [[TILE_FOG_HIDDEN for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]

    # --- 5. Generate Fluid Lifetime Map ---
    fluid_lifetime_map = [[0 for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]

    # --- 6. Reset Game Objects & State ---
    arrow_list = []
    dwarf_list = []
    flood_warnings = []
    
    gold_count = 0
    chests_found = 0
    game_over = False
    win_state = False
    current_upgrade_level = 1
    
    last_dwarf_spawn_time = pygame.time.get_ticks()
    last_fluid_update_time = pygame.time.get_ticks()

    # --- 7. Create first dwarves ---
    dwarf_1 = Dwarf(SPAWN_POINT_X, SPAWN_POINT_Y, level=1)
    dwarf_list.append(dwarf_1)
    dwarf_2 = Dwarf(SPAWN_POINT_X + 2, SPAWN_POINT_Y, level=1)
    dwarf_list.append(dwarf_2)

    dwarf_1.reveal_surroundings(fog_map)
    dwarf_2.reveal_surroundings(fog_map)
    
    # --- 8. Reset Camera ---
    center_camera_on_spawn()

def center_camera_on_spawn():
    """NEW: Helper to center the camera on the spawn point."""
    global camera_x, camera_y
    target_world_x = SPAWN_POINT_X * TILE_SIZE
    target_world_y = SPAWN_POINT_Y * TILE_SIZE
    
    camera_x = (target_world_x * zoom_level) - (WINDOW_WIDTH / 2)
    camera_y = (target_world_y * zoom_level) - ((WINDOW_HEIGHT - UI_BAR_HEIGHT) / 2)
    clamp_camera()

def seed_fluid_pockets(game_map, num_pockets, tile_type):
    pockets_placed = 0
    while pockets_placed < num_pockets:
        rand_x = random.randint(0, MAP_WIDTH - 1)
        rand_y = random.randint(0, MAP_HEIGHT - 1)
        
        current_tile_at_spot = game_map[rand_y][rand_x]
        if (current_tile_at_spot in [TILE_DIRT, TILE_HARD_DIRT, TILE_CRACKED_DIRT] and
            ((abs(rand_x - SPAWN_POINT_X) > HARD_DIRT_RADIUS) or (abs(rand_y - SPAWN_POINT_Y) > HARD_DIRT_RADIUS))):
            
            for y_offset in range(-1, 2):
                for x_offset in range(-1, 2):
                    pocket_x = rand_x + x_offset
                    pocket_y = rand_y + y_offset
                    if (0 <= pocket_x < MAP_WIDTH) and (0 <= pocket_y < MAP_HEIGHT):
                         game_map[pocket_y][pocket_x] = tile_type
            pockets_placed += 1

def perform_upgrade(dwarf_list, current_upgrade_level):
    """NEW: Robust upgrade function that loops to find dwarves."""
    if current_upgrade_level > MAX_LEVEL:
        return current_upgrade_level # Can't upgrade L5
    
    # BUGFIX: Loop until we find a level to upgrade or check all levels
    levels_checked = 0
    while levels_checked < MAX_LEVEL:
        dwarves_to_upgrade = [d for d in dwarf_list if d.level == current_upgrade_level]
        
        if dwarves_to_upgrade:
            # Found dwarves, upgrade them
            play_sound('upgrade')
            for dwarf in dwarves_to_upgrade:
                dwarf.set_level(dwarf.level + 1)
            
            # Set next level to check
            current_upgrade_level += 1
            if current_upgrade_level > MAX_LEVEL:
                current_upgrade_level = 1
            return current_upgrade_level # Success
        
        # No dwarves of this level, check next level
        current_upgrade_level += 1
        if current_upgrade_level > MAX_LEVEL:
            current_upgrade_level = 1
        levels_checked += 1
        
    # We checked all levels and found no dwarves to upgrade
    return current_upgrade_level

def give_random_tool(dwarf):
    """NEW: Gives the dwarf a tool they don't have."""
    global gold_count
    
    available_tools = []
    if not dwarf.has_pickaxe: available_tools.append('pickaxe')
    if not dwarf.has_goggles: available_tools.append('goggles')
    if not dwarf.has_ale: available_tools.append('ale')
    
    if not available_tools:
        # Dwarf has all tools! Give bonus gold.
        gold_count += 5
        play_sound('reward')
        return

    tool_to_give = random.choice(available_tools)
    
    if tool_to_give == 'pickaxe':
        dwarf.has_pickaxe = True
    elif tool_to_give == 'goggles':
        dwarf.has_goggles = True
        dwarf.reveal_surroundings(fog_map) # Instantly reveal
    elif tool_to_give == 'ale':
        dwarf.has_ale = True
        
    play_sound('upgrade') # Play upgrade sound for getting a tool

def update_fluids(game_map, fluid_lifetime_map, current_time):
    """Simulates one step of fluid physics with persistent sources and evaporation."""
    
    next_game_map = copy.deepcopy(game_map)
    # BUGFIX 1: Initialize next_lifetime_map to 0s, not a copy.
    next_lifetime_map = [[0 for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
    
    visited_map = [[False for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
    queue = []
    new_floods = []

    # --- Phase 1: Flood Fill from all sources ---
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if game_map[y][x] == TILE_WATER_SOURCE or game_map[y][x] == TILE_LAVA_SOURCE:
                queue.append((x, y))
                visited_map[y][x] = True
                next_lifetime_map[y][x] = float('inf') # Mark as connected in *new* map

    head = 0
    while head < len(queue):
        x, y = queue[head]
        head += 1
        
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < MAP_WIDTH) and (0 <= ny < MAP_HEIGHT) and not visited_map[ny][nx]:
                if game_map[ny][nx] == TILE_WATER or game_map[ny][nx] == TILE_LAVA:
                    visited_map[ny][nx] = True
                    next_lifetime_map[ny][nx] = float('inf') # Propagate "connected"
                    queue.append((nx, ny))

    # --- Phase 2: Flow, Spread, and Evaporate ---
    for y in range(MAP_HEIGHT - 1, -1, -1):
        for x in range(MAP_WIDTH):
            current_tile = game_map[y][x]
            # Check connection status from the *newly computed* map
            is_connected = (next_lifetime_map[y][x] == float('inf'))

            if current_tile == TILE_WATER_SOURCE or current_tile == TILE_LAVA_SOURCE:
                next_game_map[y][x] = current_tile
                fluid_type = TILE_WATER if current_tile == TILE_WATER_SOURCE else TILE_LAVA
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < MAP_WIDTH) and (0 <= ny < MAP_HEIGHT):
                        if game_map[ny][nx] == TILE_EMPTY:
                            next_game_map[ny][nx] = fluid_type
                            next_lifetime_map[ny][nx] = float('inf')
                            new_floods.append((nx, ny, current_time + WARNING_DURATION))

            elif current_tile == TILE_WATER or current_tile == TILE_LAVA:
                if is_connected:
                    # This fluid is alive and connected. Keep it and spread.
                    next_game_map[y][x] = current_tile
                    
                    if y + 1 < MAP_HEIGHT and game_map[y+1][x] == TILE_EMPTY:
                        next_game_map[y+1][x] = current_tile
                        next_lifetime_map[y+1][x] = float('inf')
                    elif y + 1 < MAP_HEIGHT:
                        if x - 1 >= 0 and game_map[y][x-1] == TILE_EMPTY:
                            next_game_map[y][x-1] = current_tile
                            next_lifetime_map[y][x-1] = float('inf')
                        if x + 1 < MAP_WIDTH and game_map[y][x+1] == TILE_EMPTY:
                            next_game_map[y][x+1] = current_tile
                            next_lifetime_map[y][x+1] = float('inf')
                
                else: # This fluid is ORPHANED
                    # Get lifetime from *previous* map
                    old_lifetime = fluid_lifetime_map[y][x] 
                    
                    # BUGFIX 2: Check if it *was* connected (inf), not if it was empty (0)
                    if old_lifetime == float('inf'):
                        # Was *just* disconnected. Start its timer.
                        new_lifetime = current_time + FLUID_LIFETIME
                        next_game_map[y][x] = current_tile
                        next_lifetime_map[y][x] = new_lifetime # Set timer in *new* map
                    
                    elif old_lifetime > 0: # Timer was already ticking
                        if current_time > old_lifetime:
                            # Timer is up! Evaporate.
                            next_game_map[y][x] = TILE_EMPTY
                            next_lifetime_map[y][x] = 0
                        else:
                            # Timer is ticking. Keep it, but only flow down.
                            next_game_map[y][x] = current_tile
                            next_lifetime_map[y][x] = old_lifetime # Keep timer
                            
                            if y + 1 < MAP_HEIGHT and game_map[y+1][x] == TILE_EMPTY:
                                next_game_map[y+1][x] = current_tile
                                next_lifetime_map[y+1][x] = old_lifetime # Pass timer
                                
                                # It MOVED, so clear the current tile
                                next_game_map[y][x] = TILE_EMPTY
                                next_lifetime_map[y][x] = 0
                    # If old_lifetime == 0, this tile was empty/dirt.
                    # It will be filled by a tile *above* it, if applicable.
                    # So we do nothing here.

    return next_game_map, next_lifetime_map, new_floods
        
def find_adjacent_empty_tile(x, y, game_map):
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (-1, 0)]:
        new_x, new_y = x + dx, y + dy
        if (0 <= new_x < MAP_WIDTH) and (0 <= new_y < MAP_HEIGHT):
            if game_map[new_y][new_x] == TILE_EMPTY:
                return new_x, new_y
    return x, y

def draw_minimap(surface, current_time):
    """NEW: Draws the entire game state onto the minimap surface."""
    
    flash_on = (current_time // 250) % 2 == 0
    minimap_surface.fill(MINIMAP_BG_COLOR)
    
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if fog_map[y][x] == TILE_FOG_REVEALED:
                tile_type = game_map[y][x]
                color = MINIMAP_COLORS.get(tile_type, (0,0,0))
                
                if tile_type in [TILE_WATER, TILE_LAVA, TILE_WATER_SOURCE, TILE_LAVA_SOURCE]:
                    if not flash_on:
                        color = (color[0]//2, color[1]//2, color[2]//2)
                
                mini_x = int(x * minimap_pixel_size_x)
                mini_y = int(y * minimap_pixel_size_y)
                mini_w = max(1, int((x + 1) * minimap_pixel_size_x) - mini_x)
                mini_h = max(1, int((y + 1) * minimap_pixel_size_y) - mini_y)

                pygame.draw.rect(minimap_surface, color, (mini_x, mini_y, mini_w, mini_h))

    dwarf_w = max(1, int(minimap_pixel_size_x * 2))
    dwarf_h = max(1, int(minimap_pixel_size_y * 2))
    for dwarf in dwarf_list:
        if dwarf.alive:
            mini_x = int(dwarf.x * minimap_pixel_size_x) - dwarf_w // 2
            mini_y = int(dwarf.y * minimap_pixel_size_y) - dwarf_h // 2
            pygame.draw.rect(minimap_surface, DWARF_MINIMAP_COLOR, (mini_x, mini_y, dwarf_w, dwarf_h))

    cam_world_x, cam_world_y = screen_to_world(0, UI_BAR_HEIGHT)
    cam_world_w, cam_world_h = screen_to_world(WINDOW_WIDTH, WINDOW_HEIGHT)
    
    cam_grid_x, cam_grid_y = world_to_grid(cam_world_x, cam_world_y)
    cam_grid_w, cam_grid_h = world_to_grid(cam_world_w, cam_world_h)
    cam_grid_w -= cam_grid_x
    cam_grid_h -= cam_grid_y
    
    mini_cam_x = int(cam_grid_x * minimap_pixel_size_x)
    mini_cam_y = int(cam_grid_y * minimap_pixel_size_y)
    mini_cam_w = int(cam_grid_w * minimap_pixel_size_x)
    mini_cam_h = int(cam_grid_h * minimap_pixel_size_y)
    
    pygame.draw.rect(minimap_surface, (255, 255, 255), (mini_cam_x, mini_cam_y, mini_cam_w, mini_cam_h), 1)
    pygame.draw.rect(minimap_surface, MINIMAP_BORDER_COLOR, (0, 0, MINIMAP_WIDTH, MINIMAP_HEIGHT), 1)
    
    surface.blit(minimap_surface, (MINIMAP_X, MINIMAP_Y))

def get_minimap_grid_pos(screen_x, screen_y):
    """NEW: Checks if a click is on the minimap and returns the grid pos."""
    game_area_x = screen_x
    game_area_y = screen_y - UI_BAR_HEIGHT
    
    if (MINIMAP_X <= game_area_x < MINIMAP_X + MINIMAP_WIDTH and
        MINIMAP_Y <= game_area_y < MINIMAP_Y + MINIMAP_HEIGHT):
        
        local_x = game_area_x - MINIMAP_X
        local_y = game_area_y - MINIMAP_Y
        
        percent_x = local_x / MINIMAP_WIDTH
        percent_y = local_y / MINIMAP_HEIGHT
        
        grid_x = int(percent_x * MAP_WIDTH)
        grid_y = int(percent_y * MAP_HEIGHT)
        
        return grid_x, grid_y
        
    return None

# --- Game Window & Surfaces ---
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Merge Dwarfs! v2.4 - Bugfixes!")

game_area_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT - UI_BAR_HEIGHT))

# --- Load Assets ---
load_spritesheet()
load_sounds()

# --- Game State Variables ---
game_map = []
fog_map = []
fluid_lifetime_map = []
arrow_list = []
dwarf_list = []
flood_warnings = []

gold_count = 0
chests_found = 0
game_over = False
win_state = False
current_upgrade_level = 1
last_dwarf_spawn_time = 0
last_fluid_update_time = 0
current_game_level = 1

# --- NEW: Map & Camera Globals ---
MAP_WIDTH = 0
MAP_HEIGHT = 0
TOTAL_CHESTS = 0
TOTAL_WATER_POCKETS = 0
TOTAL_LAVA_POCKETS = 0
SPAWN_POINT_X = 0
SPAWN_POINT_Y = 0
HARD_DIRT_RADIUS = 0

# NEW: Camera & Input State
camera_x = 0.0
camera_y = 0.0
zoom_level = 1.0
is_panning = False
pan_start_x = 0
pan_start_y = 0
is_paused = False
pause_button_rect = None

# NEW: Minimap Globals
minimap_surface = None
minimap_pixel_size_x = 1
minimap_pixel_size_y = 1

# --- Initial Level Setup ---
setup_level(current_game_level)

# --- Start Music ---
pygame.mixer.music.play(-1) # Loop forever

# --- Game Loop ---
running = True
clock = pygame.time.Clock()

while running:
    current_time = pygame.time.get_ticks()
    mouse_pos = pygame.mouse.get_pos()
    
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_RETURN and game_over:
                if not win_state:
                    setup_level(current_game_level)
                else:
                    current_game_level += 1
                    setup_level(current_game_level)
                
                center_camera_on_spawn()
                pygame.mixer.music.play(-1)
        
        if event.type == pygame.MOUSEWHEEL:
            old_world_x, old_world_y = screen_to_world(mouse_pos[0], mouse_pos[1] - UI_BAR_HEIGHT)
            zoom_level = max(0.2, min(3.0, zoom_level + event.y * 0.1))
            new_world_x, new_world_y = screen_to_world(mouse_pos[0], mouse_pos[1] - UI_BAR_HEIGHT)
            
            camera_x -= (new_world_x - old_world_x) * zoom_level
            camera_y -= (new_world_y - old_world_y) * zoom_level
            clamp_camera()
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            is_panning = True
            pan_start_x, pan_start_y = mouse_pos
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            is_panning = False
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if event.type == pygame.MOUSEBUTTONDOWN:
            
            if pause_button_rect and pause_button_rect.collidepoint(mouse_pos):
                is_paused = not is_paused
                if is_paused:
                    pygame.mixer.pause()
                else:
                    pygame.mixer.unpause()
                continue
            
            if not game_over:
                minimap_grid_pos = get_minimap_grid_pos(mouse_pos[0], mouse_pos[1])
                if minimap_grid_pos:
                    target_world_x = minimap_grid_pos[0] * TILE_SIZE
                    target_world_y = minimap_grid_pos[1] * TILE_SIZE
                    
                    camera_x = (target_world_x * zoom_level) - (WINDOW_WIDTH / 2)
                    camera_y = (target_world_y * zoom_level) - ((WINDOW_HEIGHT - UI_BAR_HEIGHT) / 2)
                    clamp_camera()
                    continue
                
                grid_x, grid_y = screen_to_grid(mouse_pos[0], mouse_pos[1])
                
                if grid_x != -1:
                    
                    if event.button == 1: # Left Click: Place/Cycle Arrow
                        existing_arrow = None
                        for arrow in arrow_list:
                            if arrow.x == grid_x and arrow.y == grid_y:
                                existing_arrow = arrow
                                break
                        if existing_arrow:
                            existing_arrow.cycle_direction()
                        else:
                            new_arrow = Arrow(grid_x, grid_y)
                            arrow_list.append(new_arrow)
                    
                    elif event.button == 3: # Right Click: Wall/Del Arrow
                        arrow_to_remove = None
                        for arrow in arrow_list:
                            if arrow.x == grid_x and arrow.y == grid_y:
                                arrow_to_remove = arrow
                                break
                        
                        if arrow_to_remove:
                            arrow_list.remove(arrow_to_remove)
                        else:
                            build_target_tile = game_map[grid_y][grid_x]
                            if (gold_count >= WALL_COST and 
                                build_target_tile in [TILE_EMPTY, TILE_DIRT, TILE_WATER, TILE_LAVA, TILE_HARD_DIRT, TILE_CRACKED_DIRT] and
                                fog_map[grid_y][grid_x] == TILE_FOG_REVEALED):
                                
                                game_map[grid_y][grid_x] = TILE_WALL
                                gold_count -= WALL_COST
                                fluid_lifetime_map[grid_y][grid_x] = 0

        if event.type == pygame.MOUSEMOTION and is_panning:
            dx = event.pos[0] - pan_start_x
            dy = event.pos[1] - pan_start_y
            
            camera_x -= dx
            camera_y -= dy
            clamp_camera()
            pan_start_x, pan_start_y = event.pos


    # --- Game Logic ---
    if not game_over and not is_paused:
        # --- Dwarf Spawner ---
        if current_time - last_dwarf_spawn_time > DWARF_SPAWN_DELAY:
            new_dwarf = Dwarf(SPAWN_POINT_X, SPAWN_POINT_Y, level=1)
            dwarf_list.append(new_dwarf)
            new_dwarf.reveal_surroundings(fog_map)
            last_dwarf_spawn_time = current_time
            current_upgrade_level = 1
            play_sound('spawn')
        
        # --- Fluid Simulation ---
        if current_time - last_fluid_update_time > FLUID_UPDATE_DELAY:
            game_map, fluid_lifetime_map, new_floods = update_fluids(game_map, fluid_lifetime_map, current_time)
            last_fluid_update_time = current_time
            if new_floods:
                flood_warnings.extend(new_floods)
                play_sound('warning')
        
        # --- Update all dwarves ---
        new_dwarves_from_loot = []
        trigger_free_upgrade = False
        
        for dwarf in dwarf_list:
            if dwarf.alive:
                reward = dwarf.update(game_map, fog_map, arrow_list, dwarf_list, current_time)
                
                if reward == 'gold':
                    gold_count += 1
                    play_sound('reward')
                elif reward == 'chest':
                    chests_found += 1
                    play_sound('reward')
                    if chests_found == TOTAL_CHESTS:
                        game_over = True
                        win_state = True
                        pygame.mixer.music.stop()
                        play_sound('win')
                
                # --- NEW: Updated Reward Logic ---
                elif reward == 'present':
                    give_random_tool(dwarf) # Gives pick, goggles, or ale
                
                elif reward == 'upgrade_loot': # Star
                    trigger_free_upgrade = True # Mass upgrade
                
                elif reward == 'dwarf_loot': # Heart
                    # Spawns a new L1 dwarf
                    play_sound('spawn')
                    spawn_x, spawn_y = find_adjacent_empty_tile(dwarf.x, dwarf.y, game_map)
                    new_dwarf = Dwarf(spawn_x, spawn_y, level=1)
                    new_dwarves_from_loot.append(new_dwarf)
                    new_dwarf.reveal_surroundings(fog_map)
                    current_upgrade_level = 1
                    dwarf.pick_random_direction()
                    new_dwarf.pick_random_direction()
                
                elif reward == 'cracked_dirt':
                    if random.random() < 0.5:
                        play_sound('cavein')
                        # BUGFIX: Removed flood_warnings.append line
                        
                        adjacent_empty_tiles = []
                        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1,-1), (-1,1), (1,-1), (1,1)]:
                            nx, ny = dwarf.x + dx, dwarf.y + dy
                            if (0 <= nx < MAP_WIDTH) and (0 <= ny < MAP_HEIGHT):
                                if game_map[ny][nx] == TILE_EMPTY:
                                    adjacent_empty_tiles.append((nx, ny))
                        
                        num_to_fill = random.choice([2, 3])
                        random.shuffle(adjacent_empty_tiles)
                        
                        for i in range(min(num_to_fill, len(adjacent_empty_tiles))):
                            fill_x, fill_y = adjacent_empty_tiles[i]
                            game_map[fill_y][fill_x] = TILE_DIRT
                            fluid_lifetime_map[fill_y][fill_x] = 0

        dwarf_list.extend(new_dwarves_from_loot)
        
        if trigger_free_upgrade:
            current_upgrade_level = perform_upgrade(dwarf_list, current_upgrade_level)
            
        # --- Merge Check ---
        for i in range(len(dwarf_list)):
            for j in range(i + 1, len(dwarf_list)):
                dwarf_a = dwarf_list[i]
                dwarf_b = dwarf_list[j]
                
                if (dwarf_a.alive and dwarf_b.alive and
                    dwarf_a.x == dwarf_b.x and dwarf_a.y == dwarf_b.y and
                    dwarf_a.level == dwarf_b.level and dwarf_a.level < MAX_LEVEL):
                    
                    dwarf_a.set_level(dwarf_a.level + 1)
                    dwarf_b.alive = False
                    play_sound('upgrade')

        # --- Cleanup ---
        dwarf_list = [d for d in dwarf_list if d.alive]
        
        # --- Check for Game Over ---
        if not dwarf_list and not (game_over and win_state):
            game_over = True
            win_state = False
            pygame.mixer.music.stop()


    # --- Drawing ---
    
    screen.fill(COLOR_UI_BACKGROUND)
    game_area_surface.fill(COLOR_FOG_HIDDEN)
    
    scale_sprites(zoom_level)
    current_tile_size = int(TILE_SIZE * zoom_level)
    
    if current_tile_size > 0:
        view_world_x_start, view_world_y_start = screen_to_world(0, 0)
        view_world_x_end, view_world_y_end = screen_to_world(WINDOW_WIDTH, WINDOW_HEIGHT - UI_BAR_HEIGHT)

        tile_col_start = max(0, int(view_world_x_start / TILE_SIZE) - 1)
        tile_col_end = min(MAP_WIDTH, int(view_world_x_end / TILE_SIZE) + 2)
        tile_row_start = max(0, int(view_world_y_start / TILE_SIZE) - 1)
        tile_row_end = min(MAP_HEIGHT, int(view_world_y_end / TILE_SIZE) + 2)

        # --- Draw Layer 1: Base Terrain (Floor) ---
        for row in range(tile_row_start, tile_row_end):
            for col in range(tile_col_start, tile_col_end):
                
                if fog_map[row][col] == TILE_FOG_REVEALED:
                    screen_x, screen_y = world_to_screen(col * TILE_SIZE, row * TILE_SIZE)
                    tile_type = game_map[row][col]
                    
                    sprite_to_draw = sprite_cache.get('TILE_EMPTY')
                    if tile_type == TILE_DIRT:
                        sprite_to_draw = sprite_cache.get('TILE_DIRT')
                    elif tile_type == TILE_HARD_DIRT:
                        sprite_to_draw = sprite_cache.get('TILE_HARD_DIRT')
                    elif tile_type == TILE_CRACKED_DIRT:
                        sprite_to_draw = sprite_cache.get('TILE_CRACKED_DIRT')
                    elif tile_type == TILE_WALL:
                        sprite_to_draw = sprite_cache.get('TILE_WALL')
                    elif tile_type == TILE_WATER:
                        sprite_to_draw = sprite_cache.get('TILE_WATER')
                    elif tile_type == TILE_LAVA:
                        sprite_to_draw = sprite_cache.get('TILE_LAVA')
                    elif tile_type == TILE_WATER_SOURCE:
                        sprite_to_draw = sprite_cache.get('TILE_WATER_SOURCE')
                    elif tile_type == TILE_LAVA_SOURCE:
                        sprite_to_draw = sprite_cache.get('TILE_LAVA_SOURCE')
                    elif tile_type in [TILE_GOLD, TILE_PRESENT, TILE_CHEST, TILE_UPGRADE_LOOT, TILE_DWARF_LOOT]:
                        distance = math.sqrt((col - SPAWN_POINT_X)**2 + (row - SPAWN_POINT_Y)**2)
                        if distance > HARD_DIRT_RADIUS:
                             sprite_to_draw = sprite_cache.get('TILE_HARD_DIRT')
                        else:
                             sprite_to_draw = sprite_cache.get('TILE_DIRT')
                    
                    if sprite_to_draw:
                        game_area_surface.blit(sprite_to_draw, (screen_x, screen_y))
                    
                    if current_tile_size > 5:
                        pygame.draw.rect(game_area_surface, COLOR_GRID, (screen_x, screen_y, current_tile_size, current_tile_size), 1)

        # --- Draw Layer 2: Loot (On top of terrain) ---
        for row in range(tile_row_start, tile_row_end):
            for col in range(tile_col_start, tile_col_end):
                if fog_map[row][col] == TILE_FOG_REVEALED:
                    tile_type = game_map[row][col]
                    
                    sprite_to_draw = None
                    if tile_type == TILE_GOLD: sprite_to_draw = sprite_cache.get('TILE_GOLD')
                    elif tile_type == TILE_PRESENT: sprite_to_draw = sprite_cache.get('TILE_PRESENT')
                    elif tile_type == TILE_CHEST: sprite_to_draw = sprite_cache.get('TILE_CHEST')
                    elif tile_type == TILE_UPGRADE_LOOT: sprite_to_draw = sprite_cache.get('TILE_UPGRADE_LOOT')
                    elif tile_type == TILE_DWARF_LOOT: sprite_to_draw = sprite_cache.get('TILE_DWARF_LOOT')
                    
                    if sprite_to_draw:
                        screen_x, screen_y = world_to_screen(col * TILE_SIZE, row * TILE_SIZE)
                        game_area_surface.blit(sprite_to_draw, (screen_x, screen_y))

    # --- Draw Layer 3: Dwarves (Drawn outside tile loop) ---
    if current_tile_size > 0:
        for dwarf in dwarf_list:
            if dwarf.alive:
                screen_x, screen_y = world_to_screen(dwarf.x * TILE_SIZE, dwarf.y * TILE_SIZE)
                if screen_x > -current_tile_size and screen_x < WINDOW_WIDTH and \
                   screen_y > -current_tile_size and screen_y < (WINDOW_HEIGHT - UI_BAR_HEIGHT):
                    scaled_sprite = sprite_cache.get(dwarf.sprite_key)
                    if scaled_sprite:
                        dwarf.draw(game_area_surface, screen_x, screen_y, scaled_sprite)

    # --- Draw Layer 4: Arrows ---
    if current_tile_size > 0:
        for arrow in arrow_list:
            screen_x, screen_y = world_to_screen(arrow.x * TILE_SIZE, arrow.y * TILE_SIZE)
            if screen_x > -current_tile_size and screen_x < WINDOW_WIDTH and \
               screen_y > -current_tile_size and screen_y < (WINDOW_HEIGHT - UI_BAR_HEIGHT):
                scaled_sprite = sprite_cache.get(arrow.sprite_key)
                if scaled_sprite:
                    arrow.draw(game_area_surface, screen_x, screen_y, scaled_sprite)
                
    # --- Draw Layer 5: Flood Warnings ---
    flood_warnings = [w for w in flood_warnings if w[2] > current_time]
    for (x, y, expiry_time) in flood_warnings:
        world_x = (x + 0.5) * TILE_SIZE
        world_y = (y + 0.5) * TILE_SIZE
        screen_x, screen_y = world_to_screen(world_x, world_y)
        
        time_left = expiry_time - current_time
        alpha = (time_left / WARNING_DURATION)
        radius = int((1 - alpha) * 3 * TILE_SIZE * zoom_level)
        
        if radius > 0 and (0 < screen_x < WINDOW_WIDTH) and (0 < screen_y < (WINDOW_HEIGHT - UI_BAR_HEIGHT)):
            try:
                warning_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(warning_surface, (255, 0, 0, int(alpha * 200)), (radius, radius), radius, max(1, int(zoom_level * 2)))
                game_area_surface.blit(warning_surface, (screen_x - radius, screen_y - radius))
            except pygame.error:
                pass

    # --- NEW: Draw PAUSED Overlay ---
    if is_paused:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT - UI_BAR_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        game_area_surface.blit(overlay, (0, 0))
        
        paused_text = UI_FONT_GAMEOVER.render("PAUSED", True, COLOR_UI_TEXT)
        text_rect = paused_text.get_rect(center=(WINDOW_WIDTH // 2, (WINDOW_HEIGHT - UI_BAR_HEIGHT) // 2))
        game_area_surface.blit(paused_text, text_rect)

    # --- Draw Layer 6: Minimap ---
    if minimap_surface:
        draw_minimap(game_area_surface, current_time)

    # --- Final Blit ---
    screen.blit(game_area_surface, (0, UI_BAR_HEIGHT))

    # --- Draw UI (Always on top, in screen space) ---
    gold_text = UI_FONT.render(f"Gold: {gold_count}", True, COLOR_UI_TEXT)
    chests_text = UI_FONT.render(f"Chests: {chests_found} / {TOTAL_CHESTS}", True, COLOR_UI_TEXT)
    level_text = UI_FONT.render(f"Level: {current_game_level}", True, COLOR_UI_TEXT)
    screen.blit(gold_text, (10, 10))
    screen.blit(chests_text, (10, 30))
    screen.blit(level_text, (130, 10))
    
    controls_text_1 = UI_FONT_CONTROLS.render("L-Click: Arrow | R-Click: Wall/Del Arrow", True, CONTROL_TEXT_COLOR)
    controls_text_2 = UI_FONT_CONTROLS.render("M-Click Drag: Pan | Wheel: Zoom", True, CONTROL_TEXT_COLOR)
    screen.blit(controls_text_1, (220, 12))
    screen.blit(controls_text_2, (220, 32))
    
    pause_text_str = "[ | | Pause ]" if not is_paused else "[ > Play ]"
    pause_text = UI_FONT.render(pause_text_str, True, COLOR_UI_TEXT)
    pause_button_rect = pause_text.get_rect(topright=(WINDOW_WIDTH - 20, 10))
    
    button_bg_rect = pause_button_rect.inflate(10, 6)
    pygame.draw.rect(screen, (50, 50, 50), button_bg_rect, 0, 3)
    pygame.draw.rect(screen, (100, 100, 100), button_bg_rect, 1, 3)
    
    screen.blit(pause_text, pause_button_rect)
    
    # --- Draw Game Over / Win Screen ---
    if game_over:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        if win_state:
            text = UI_FONT_GAMEOVER.render("YOU WIN!", True, WIN_TEXT_COLOR)
            prompt = UI_FONT.render(f"Press [ENTER] to start Level {current_game_level + 1}", True, COLOR_UI_TEXT)
        else:
            text = UI_FONT_GAMEOVER.render("GAME OVER", True, GAMEOVER_TEXT_COLOR)
            prompt = UI_FONT.render(f"Press [ENTER] to restart Level {current_game_level}", True, COLOR_UI_TEXT)
            
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
        prompt_rect = prompt.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
        screen.blit(text, text_rect)
        screen.blit(prompt, prompt_rect)


    # --- Update Display ---
    pygame.display.flip()
    clock.tick(60) # Cap at 60 FPS

# --- Shutdown ---
pygame.quit()
sys.exit()

