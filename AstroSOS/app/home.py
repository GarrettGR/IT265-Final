import json
import os
from flask import Flask, request, jsonify
from threading import Lock
from app import app
from app import hello
import logging
import traceback
from logging import FileHandler

data_file = 'data.json'
save_file = 'save.json'
lock = Lock()

request_handler = FileHandler('requests.log')
request_handler.setLevel(logging.DEBUG)

error_handler = FileHandler('errors.log')
error_handler.setLevel(logging.ERROR)

state_handler = FileHandler('app.log')
state_handler.setLevel(logging.DEBUG)

request_logger = logging.getLogger('request')
request_logger.setLevel(logging.DEBUG)
request_logger.addHandler(request_handler)

error_logger = logging.getLogger('error')
error_logger.setLevel(logging.ERROR)
error_logger.addHandler(error_handler)

state_logger = logging.getLogger('state')
state_logger.setLevel(logging.DEBUG)
state_logger.addHandler(state_handler)

@app.before_request
def log_request_info():
    request_logger.debug('\n\n Headers: %s', request.headers)
    request_logger.debug('Body: %s', request.get_data())

@app.after_request
def log_response_info(response):
    request_logger.debug('\n\n Response: %s', response.get_data())
    return response

@app.errorhandler(500)
def handle_500(error):
    error_logger.error('\n\n 500 error: %s', traceback.format_exc())
    return jsonify(error=str(error)), 500

#? maybe I should have just used @dataclass ...
class Room:
    id_counter = 0
    def __init__(self, name, description, items, characters, connections={}, other={}, id=None):
        self.name = name
        self.description = description
        self.items = items
        self.characters = characters
        self.connections = connections
        self.other = other
        self.id = Room.id_counter if id is None else id
        Room.id_counter += 1

    def __str__(self):
        return f'Room : ({self.name}, {self.description}, {self.items}, {self.characters}, {self.connections}, {self.other})'
    
    def __dict__(self):
        return {'name': self.name, 'description': self.description, 'items': self.items, 'characters': self.characters, 'connections': self.connections, 'other': self.other}
    
    def to_json(self):
        return {
            'name': self.name,
            'description': self.description,
            'items': [item.to_json() for item in self.items],
            'characters': [character.to_json() for character in self.characters],
            'connections': {direction: {'name': room.name, 'description': room.description, 'other': {key: value.to_json() if hasattr(value, 'to_json') else value for key, value in room.other.items()}} for direction, room in self.connections.items() if room is not None},
            'other': {key: value.to_json() if hasattr(value, 'to_json') else value for key, value in self.other.items()}
        }
        
    def save(self):
        return {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'items': [item.id for item in self.items],
            'characters': [character.id for character in self.characters],
            'connections': {direction: room.id for direction, room in self.connections.items()},
            'other': {key: value.to_json() if hasattr(value, 'to_json') else value for key, value in self.other.items()}
        }

class Character:
    id_counter = 0
    def __init__(self, name, description, health, location: Room = None, visits=0, id=None):
        self.name = name
        self.description = description
        self.health = health
        self.location = location
        self.visits = visits
        self.id = Character.id_counter  if id is None else id
        Character.id_counter += 1
        
    def __str__(self):
        return f'Person : {self.name}, {self.description}, {str(self.health)}'
    
    def __dict__(self):
        return {'name': self.name, 'description': self.description, 'health': self.health, 'location': self.location, 'visits': self.visits}
    
    def to_json(self):
        return {
            'name': self.name,
            'description': self.description,
            'health': self.health,
            'visits': self.visits
        }
    
    def save(self):
        return {
            'name': self.name,
            'id' : self.id,
            'description': self.description,
            'health': self.health,
            'location': self.location.id,
            'visits': self.visits
        }
        
class Player:
    def __init__(self, name, health=3, location: Room = None, inventory=[], input_position=0):
        self.name = name
        self.location = location
        self.inventory = inventory
        self.health = health
        self.input_position = input_position
        
    def __str__(self):
        return f'Player : {self.name}, {str(self.health)}'
    
    def __dict__(self):
        return {'name': self.name, 'location': self.location, 'inventory': self.inventory, 'health': self.health, 'input_position': self.input_position}
    
    def to_json(self):
        return {
            'name': self.name,
            'location': self.location.to_json(),
            'inventory': [item.to_json() for item in self.inventory],
            'health': self.health,
            'input_position': self.input_position,
        }
        
    def save(self):
        return {
            'name': self.name,
            'location': self.location.id,
            'inventory': [item.id for item in self.inventory],
            'health': self.health,
            'input_position': self.input_position,
        }
                
class Item:
    id_counter = 0
    def __init__(self, name, description, other={}, id=None):
        self.name = name
        self.description = description
        self.other = other
        self.id = Item.id_counter if id is None else id
        Item.id_counter += 1
        
    def __str__(self):
        return f'Item : ({self.name}, {self.description})'
    
    def __dict__(self):
        return {'name': self.name, 'description': self.description, 'other': self.other}
    
    def use (self):
        return "You used the " + self.name
    
    def to_json(self):
        return {
            'name': self.name,
            'description': self.description,
            'other': self.other,
            'id': self.id
        }
        
# -------------------------------------------------------------------------

def initialize_game_state():
            
    keycard = Item('key card', 'A key card with the name "Jake" on it')
    firstaid = Item('first aid kit', 'A first aid kit with a red cross on it')
    firstaid2 = Item('first aid kit', 'A first aid kit with a red cross on it')
    crowbar = Item('crowbar', 'A crowbar that looks sturdy for how light it is')

    fireExtinguiser = Item('fire extinguisher', 'A fire extinguisher with a pin in it')
    flashLight = Item('flashlight', 'A flashlight with a broken bulb', {'bulb': 0})

    logBook = Item('log book', 'A log book hidden in a desk drawer, it seems to have details on the secret process of getting into the engineering chamber\'s restricted area')

    secretCode = Item('secret code', 'A piece of paper with a code on it, it looks like it could be used to access something...', {'code': '56733'})
    waterRation = Item('water ration', 'A water ration with a label that says "Zephyr"')
    foodRation = Item('food ration', 'A food ration with a label that says "Zephyr"... how did he get into this room?')
        
    Jake = Character('Jake', 'A young medical tech who lookes injured on their side', 2)
    Melanie = Character('Melanie', 'An injured engineer pinned by a steel gurder which appears to be embedded in the station\'s wall, she calls for help', 1)
    Zypher = Character('Zephyr', 'Almost a child, a young trainee in shock and hiding in a closet', 3)

    start = Room('Cryo', 'A dark room filled with cryro chambers where you woke up', [keycard, firstaid, crowbar], [Jake], other={'hidden_item': firstaid2})
    corridor = Room('Corridor', 'A long corridor with a door at the end, you see a steel beam fallen on top of a woman wearing an engineers\'s jumpsuit and hear her calling for help, you see flickering flames inbetween yourself and the enginerer, but you also see a fire extinguisher in the wall!', [fireExtinguiser, flashLight], [Melanie], other={'fire': True, 'lights': False, 'incomplete_description': 'A long corridor with a door at the end, you hear shouts but there are no lights at the moment'}) 
    offices = Room('Offices', 'A room with a few desks and a door to the north', [], [Zypher], other={'hidden_item': logBook})
    engineering = Room('Engineering', 'A room with a large machine in the center, there is more equipment that seems to be unpowered, but the computer controls are locked down behind a patern-based password', [], [], other={'minigame': 'life support'})
    storage = Room ('Storage', 'A room with a few shelves and a door to the south', [secretCode, waterRation, foodRation], [], other={'hidden': True})

    Jake.location = start
    Melanie.location = corridor
    Zypher.location = offices

    start.connections = {'west': corridor}
    corridor.connections = {'east': start, 'north': offices, 'west': engineering}
    offices.connections = {'south': corridor}
    engineering.connections = {'east': corridor, 'south': storage}
    storage.connections = {'north': engineering}

    player = Player('Garrett', location=start)

    gameState = {
        'player': player,
        'items': [keycard, firstaid, crowbar, fireExtinguiser, flashLight, logBook, secretCode, waterRation, foodRation],
        'characters': [Jake, Melanie, Zypher],
        'rooms': [start, corridor, offices, engineering, storage]
    }
    
    return gameState

gameState = initialize_game_state()

# --------------------------------------------------------------------------
    
def SemanticParsing(userInput):
    def getNouns():
        nouns = ['north', 'south', 'east', 'west']
        nouns.extend([item.name.lower() for item in gameState['player'].inventory])
        nouns.append(gameState['player'].location.name.lower())
        nouns.extend([item.name.lower() for item in gameState['player'].location.items])
        nouns.extend([character.name.lower() for character in gameState['player'].location.characters])
        return nouns
    
    def examine(meaning):
        if meaning['wordType'] == 'room':
            if meaning['wordType'] == 'room':
                if meaning['noun'] != gameState["player"].location.name.lower():
                    return "error: That room is not available in this room"
                elif gameState["player"].location.other.get('lights') == False:
                    return gameState['player'].location.other.get('incomplete_description')
                else:
                    return f'{gameState["player"].location.description} and has the following items: {", ".join([item.name for item in gameState["player"].location.items])} and the following characters: {", ".join([character.name for character in gameState["player"].location.characters])}'
            elif meaning['wordType'] == 'item':
                item = next((item for item in gameState["player"].inventory if item.name == meaning['noun']), None)
                if item:
                    return item.description
                else:
                    return "error: That item is not available in this room"
            elif meaning['wordType'] == 'character':
                character = next((character for character in gameState["player"].location.characters if character.name == meaning['noun']), None)
                if character:
                    return character.description
                else:
                    return "error: That character is not available in this room"
            else:
                return "error: That noun is not available in this room"

    def take(meaning):
        item = next((item for item in gameState["player"].location.items if item.name.lower() == meaning['noun']), None)
        if item:
            gameState["player"].inventory.append(item)
            gameState["player"].location.items.remove(item)
            return "You took the " + item.name
        else:
            return "Error: That item is not available in this room"

    def drop(meaning):
        item = next((item for item in gameState["player"].inventory if item.name == meaning['noun']), None)
        if item:
            gameState["player"].location.items.append(item)
            gameState["player"].inventory.remove(item)
            return "Error: You dropped the " + item.name
        else:
            return "Error: You don't have that item in your inventory"

    def go(meaning):
        location = gameState["player"].location
        if meaning['noun'] == 'north':
            if 'north' in location.connections:
                location = location.connections['north']
                gameState["player"].location = location
                gameState['player'].input_position += 1
                return "You went North"
            else:
                return "Error: There is no room to the North"
        elif meaning['noun'] == 'south':
            if 'south' in location.connections:
                location = location.connections['south']
                gameState["player"].location = location
                gameState['player'].input_position += 1
                return "You went South"
            else:
                return "Error: There is no room to the South"
        elif meaning['noun'] == 'east':
            if 'east' in location.connections:
                location = location.connections['east']
                gameState["player"].location = location
                gameState['player'].input_position += 1
                return "You went East"
            else:
                return "Error: There is no room to the East"
        elif meaning['noun'] == 'west':
            if 'west' in location.connections:
                location = location.connections['west']
                if gameState["player"].location.other.get('fire') == True:
                    return "You can not get to Melanie to help her because of the fire in your way"
                gameState["player"].location = location
                gameState['player'].input_position += 1
                return "You went West"
            else:
                return "Error: There is no room to the West"
        else:
            return "Error: Invalid direction"
    
    def use(meaning):
        item = next((item for item in gameState["player"].inventory if item.name == meaning['noun']), None)
        if item is None:
            return "error: That item is not available in your inventory or in this room"
        if item:
            def use_key_card(gameState, item):
                location = gameState["player"].location
                if location.name == 'Engineering' and location.other.get('minigame') == 'life support' and location.other.get('code') == '56733':
                    return "You used the key card to access the life support system, you have won the game!"
                elif location.name == 'Engineering' and location.other.get('minigame') == 'solved':
                    return "You used the key card to access the life support system, but the code was wrong, you have lost the game!"
                else:
                    return "You used the key card, but nothing happened"
                
            def use_first_aid_kit(gameState, item):
                player = gameState["player"]
                health_before = player.health
                if player.health < 4:
                    player.health += 2
                    if player.health > 4:
                        player.health = 4
                    player.inventory.remove(item)
                    return f'You used the first aid kit and recovered {player.health - health_before} health'
                else:
                    return "You used the first aid kit, but you are already at full health"
                
            def use_crowbar(gameState, item):
                location = gameState["player"].location
                mel = next((character for character in location.characters if character.name == 'Melanie'), None)
                if location.name == 'Corridor' and mel.visits == 0:
                    if location.other['fire'] == True:
                        return "You can not get to Melanie to help her because of the fire in your way"
                    return "You used the crowbar to pry the steel gurder off of Melanie, she is now free and can be helped, but she is badly injured"
                elif location.other.get('hidden_item'):
                    item = location.other.get('hidden_item')
                    gameState["player"].inventory.append(item)
                    location.other.pop('hidden_item', None)
                    return f'You used the crowbar to pry open the desk drawer, you found a {item.name} and added it to your inventory'
                else:
                    return "You used the crowbar, but nothing happened"
                
            def use_fire_extinguisher(gameState, item):
                location = gameState["player"].location
                if location.name == 'Corridor' and location.other.get('fire') == True:
                    location.other['fire'] = False
                    gameState["player"].inventory.remove(item)
                    return "You used the fire extinguisher to put out the fire, you can now get to the door at the end of the corridor and the person calling for help"
                else:
                    return "There is no fire to put out"
                
            def use_flashlight(gameState, item):
                location = gameState["player"].location
                if location.other.get('lights') == False:
                    return f'You used the flashlight to see the in the dark, you can now see the room around you more clearly: <br> {location.description}'
                else:
                    return "You used the flashlight, but didn't see anything new"
                
            def use_log_book(gameState, item):
                location = gameState["player"].location
                if location.name == 'Engineering' and location.other.get('minigame') == 'life support':
                    location.other['minigame'] = 'solved'
                    return "You used the log book to find the code for the life support system, you can now use the key card to access the life support system"
                else:
                    return "You used the log book, but dont see anything useful"

            item_functions = {
                'key card': use_key_card,
                'first aid kit': use_first_aid_kit,
                'crowbar': use_crowbar,
                'fire extinguisher': use_fire_extinguisher,
                'flashlight': use_flashlight,
                'log book': use_log_book
            }

            item_name = item.name
            if item_name in item_functions:
                    return item_functions[item_name](gameState, item)
            else:
                return "error: You cannot use the " + item_name
                    
    def inventory():
        if len(gameState["player"].inventory) == 0:
            return "Your pockets are empty"
        else:
            return f'You have {str(len(gameState["player"].inventory))} items in your inventory: {", ".join([item.name for item in gameState["player"].inventory])}'

            
    def help():
        return "Examples of valid verb/noun combinations: <br> > 'Examine North' <br> > 'Take key card' <br> > 'Drop key card' <br> > 'Go North' <br> > 'Use key card' <br>  > 'Inventory'"
    
    global gameState
    userInput = ''.join(c for c in userInput if c.isalpha() or c.isspace()).lower()
    
    if userInput == 'examine':
        if gameState["player"].location.other.get('lights') == False:
            return gameState["player"].location.other.get('incomplete_description')
        return gameState["player"].location.description
    elif userInput == 'inventory':
        return inventory()
    elif userInput == 'help':
        return help()
    
    verbs = ['examine', 'take', 'drop', 'go', 'use', 'inventory', 'help']
    nouns = getNouns()
    directions = ['north', 'south', 'east', 'west']     
    words = userInput.split()
    word_types = {
        'item': gameState["items"],
        'character': gameState["characters"],
        'room': gameState["rooms"],
        'direction': directions
    }
    verb_functions = {
        'examine': examine,
        'take': take,
        'drop': drop,
        'go': go,
        'use': use,
        'inventory': inventory,
        'help': help
    }
    meaning = {
        'verb': None,
        'noun': None,
        'wordType': None
    }
    
    for word in words:
        if word in verbs:
            meaning['verb'] = word

    for noun in nouns:
        if noun in userInput:
            meaning['noun'] = noun
            break

    if meaning['verb'] is None:
        return "error: No verb found"
    elif meaning['noun'] is None:
        return "error: No noun found"

    for word_type, wordsList in word_types.items():
        for word in wordsList:
            if (word.name.lower() if hasattr(word, 'name') else word.lower()) == meaning['noun']:
                meaning['wordType'] = word_type
                break
        if meaning['wordType'] is not None:
            break

    if meaning['wordType'] is None:
        return "error: No type found"

    if meaning['verb'] in verb_functions:
        return verb_functions[meaning['verb']](meaning)
    else:
        return "error: No verb found"
             
# ----------------------------------------------

@app.route('/flask/')
def index():
    html='''
        <!DOCTYPE html>
        <h3> This is the Backend for AstroSOS, return to the <a href="https://astrosos.garrettgr.com">Frontend</a> to play the game. </h3>

        <p> If you want to get a greeting from our flask server, go to <a href="/flask/hello">Hello</a></p>
        <p> If you want to see the JSON, go to <a href="/flask/json">JSON</a> </p>
        '''
    return html

#! literally just a request to the backend to use the 'second' worker process of uWSGI so that the game really only *runs* on 'one process'
        # hey its bad but i've spent nearly 11 hours doing NOTHING but trying to debug with the multiple interpreters...
@app.route('/flask/second-process', methods=['POST'])
def something():
    logging.debug('...something?')
    return 'something?'

@app.route('/flask/reset', methods=['POST'])
def reset():
    global gameState
    
    gameState = initialize_game_state()
    prompt = f'Hello {gameState["player"].name}, you are in the {gameState["player"].location.name}. {gameState["player"].location.description}'
    
    with lock:
        with open(data_file, 'w') as f:
            json.dump({"user_inputs": [], 'prompt_outputs': [prompt]}, f)
    
    return jsonify({'message': 'reset','player': gameState["player"].to_json(), 'history': {'user_inputs': [], 'prompt_outputs': [prompt]}})

@app.route('/flask/post', methods=['POST'])
def post():
    req_json = request.get_json()
    if 'userInput' in req_json:
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
        else:
            data = {'user_inputs': [], 'prompt_outputs': []}
        
        global gameState
        userInput = req_json['userInput']
        
        if userInput != '':

            data['user_inputs'].append(req_json['userInput'])
            
            
            prompt = SemanticParsing(userInput)
                
            data['prompt_outputs'].append(prompt)

            with open(data_file, 'w') as f:
                json.dump(data, f)
                                
        state = f'''
            \n\n POST State:
            \n Items: {[item.to_json() for item in gameState["items"]]}
            \n Characters: {[character.to_json() for character in gameState["characters"]]}
            \n Rooms: {[room.to_json() for room in gameState["rooms"]]}
            \n Player: {gameState["player"].to_json()}
            '''
        state_logger.debug(state)
    else:
        return jsonify({'message': 'No userInput in the JSON request'}), 400
    
    return jsonify({'message': 'JSON posted', 'player': gameState["player"].to_json(), 'history': data})

@app.route('/flask/gameState')
def get_gameState():
    global gameState
    
    with lock:
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
        else:
            data = {'user_inputs': [], 'prompt_outputs': []}
    def pretty_print_dict(d, indent=0):
        html = ""
        for key, value in d.items() if not None else []:
            html += '<div style="margin-left: {}em">'.format(indent)
            if isinstance(value, dict):
                html += '<strong>{}</strong>:<br>'.format(key)
                html += pretty_print_dict(value, indent+1)
            else:
                html += '<strong>{}</strong>: {}'.format(key, str(value)) + "<br>"
            html += '</div>'
        return html

    html = '<! DOCTYPE html><h3>player</h3> \n  <p><strong>"player:": </strong><br>' + pretty_print_dict(gameState["player"].to_json()) + '</p> \n\n <h3>user_inputs:</h3> \n <p><strong>"user_inputs": </strong>' + str(data["user_inputs"]) + '</p> \n\n <h3>gameState:</h3> \n <p><strong>"items": </strong> <br>' + ''.join([pretty_print_dict(item.to_json()) for item in gameState["items"]]) + ', <br><br> <strong>"character": </strong><br>' + ''.join([pretty_print_dict(character.to_json()) for character in gameState["characters"]]) + ', <br><br> <strong>"rooms":</strong> <br>' + ''.join([pretty_print_dict(room.to_json()) for room in gameState["rooms"]]) + ' </p>'
    html += '<script>setTimeout(function(){location.reload()}, 5000);</script>'

    return html

@app.route('/flask/save', methods=['POST'])
def saveGame():
    global gameState
    
    history = {}
    with open(data_file, 'r') as f:
        history = json.load(f)
        
    saveData = {
        'player': gameState["player"].save(),
        'items': [item.to_json() for item in gameState["items"]],
        'characters': [character.save() for character in gameState["characters"]],
        'rooms': [room.save() for room in gameState["rooms"]],
        'history': history
    }
    
    with open(save_file, 'w') as f:
        json.dump(saveData, f)
        
    return jsonify({'message': 'Game saved'})

@app.route('/flask/load', methods=['POST'])
def loadGame():
    
    def getEntityByID(id, entities):
        for entity in entities:
            if entity.id == id:
                return entity
        error_logger.warning('Failed to find entity with ID: %s', id)
        return None
        
    global gameState
    
    with open(save_file, 'r') as f:
        saveData = json.load(f)
        
    with open(data_file, 'w') as f:
        json.dump(saveData['history'], f)
        
    items = []
    characters = []
    rooms = []
    
    for item in saveData['items']:
        items.append(Item(item['name'], item['description'], item['other'], id=item['id']))
    gameState["items"] = items
    
    for character in saveData['characters']:
        characters.append(Character(character['name'], character['description'], character['health'], character['location'], character['visits'], id=character['id']))
        
    for room in saveData['rooms']:
        itemsInRoom = []
        charactersInRoom = []
        connections = {}
        for item in room['items']:
            itemEntity = getEntityByID(item, items)
            if itemEntity is not None:
                itemsInRoom.append(itemEntity)
        for character in room['characters']:
            charactersInRoom.append(getEntityByID(character, characters))
        for direction, roomConnection in room['connections'].items():
            connections[direction] = roomConnection
        rooms.append(Room(room['name'], room['description'], itemsInRoom, charactersInRoom, connections,{key: value['id'] if isinstance(value, dict) and 'id' in value else value for key, value in room['other'].items()}, id=room['id']))
    
    for character in characters:
        character.location = getEntityByID(character.location, characters)
    gameState["characters"] = characters
    
    for room in rooms:
        for direction, roomConnection in room.connections.copy().items():
            room.connections[direction] = getEntityByID(roomConnection, rooms)
    gameState["rooms"] = rooms
            
    player = Player(saveData['player']['name'], saveData['player']['health'], saveData['player']['location'], saveData['player']['inventory'], saveData['player']['input_position'])
    
    for item in player.inventory:
        item = getEntityByID(item, items)
    player.location = getEntityByID(player.location, rooms)
    
    Item.id_counter = max(item.id for item in items) + 1
    Character.id_counter = max(character.id for character in characters) + 1
    Room.id_counter = max(room.id for room in rooms) + 1
    
    return jsonify({'message': 'game loaded', 'player': gameState["player"].to_json(), 'history': saveData['history']})

    
if __name__ == '__main__':
    app.run(debug=True)