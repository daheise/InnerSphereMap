import os
import io
import sys
from os import chdir, getcwd
from os.path import realpath
import json
import random
import math
import statistics
from collections import OrderedDict

SCRIPTDIR=os.path.dirname(os.path.realpath(__file__))
# Assume Steam
BATTLETECH_INSTALL_DIR=os.path.realpath("C:\Program Files (x86)\Steam\steamapps\common\BATTLETECH")
VANILLA_ITEMCOLLECTION_DEFS=os.path.realpath("C:\Program Files (x86)\Steam\steamapps\common\BATTLETECH\BattleTech_Data\StreamingAssets\data\itemCollections")
DIFFICULTY_MODS = {
    'planet_civ_innersphere': 1,
    'planet_civ_primitive': 0, # Periphery Civ
    'planet_climate_arctic': 7/5.0,
    'planet_climate_arid': 5/5.0,
    'planet_climate_desertempt': 4/5.0,
    'planet_climate_ice': 6/5.0,
    'planet_climate_lunar': 1/5.0,
    'planet_climate_mars': 3/5.0,
    'planet_climate_rocky': 2/5.0, # Inhospital tectonics
    'planet_climate_terran': 10/5.0,
    'planet_climate_tropical': 9/5.0,
    'planet_climate_water': 8/5.0,
    'planet_feature_asteroids': -0.1,
    'planet_feature_comet': 0.1,
    'planet_feature_gasgiant': 0,
    'planet_feature_moon01': 0.1,
    'planet_feature_moon02': 0.1,
    'planet_feature_moon03': 0.1,
    'planet_feature_rings': -0.1,
    'planet_industry_agriculture': 0.25,
    'planet_industry_aquaculture': 0.25,
    'planet_industry_manufacturing': 0.5,
    'planet_industry_mining': 0.25,
    'planet_industry_poor': 0, # Low resources
    'planet_industry_recreation': 0.25,
    'planet_industry_research': 0.5,
    'planet_industry_rich': 0.25, # High rescources
    'planet_other_alienvegetation': -.1, # Inhospitable veg
    'planet_other_blackmarket': 0,
    'planet_other_boreholes': 0.1,
    'planet_other_capital': 100,
    'planet_other_comstar': .25,
    'planet_other_empty': -100, # Uninhabited
    'planet_other_floatingworld': -.1,
    'planet_other_fungus': -.1,
    'planet_other_hub': .5,
    'planet_other_megacity': 1,
    'planet_other_megaforest': -.1,
    'planet_other_moon': 0.25,
    'planet_other_mudflats': -0.1, # Global mudflats
    'planet_other_newcolony': 0.25,
    'planet_other_pirate': 0,
    'planet_other_prison': 0,
    'planet_other_starleague': 1,
    'planet_other_stonedcaribou': -0.1,
    'planet_other_storms': -.1,
    'planet_other_taintedair': -.5,
    'planet_other_volcanic': -.5,
    'planet_pop_large': 1,
    'planet_pop_medium': .5,
    'planet_pop_none': -1, #
    'planet_pop_small': .25, #
    'planet_ruins': 0.25,
    'planet_size_large': -1,
    'planet_size_medium': 1,
    'planet_size_small': -1,
    # Customs tags
    'planet_other_borderworld': 1,
    }


class PushdContext:
    cwd = None
    original_dir = None

    def __init__(self, dirname):
        self.cwd = realpath(dirname)

    def __enter__(self):
        self.original_dir = getcwd()
        chdir(self.cwd)
        return self

    def __exit__(self, type, value, tb):
        chdir(self.original_dir)

def pushd(dirname):
    return PushdContext(dirname)

systems_3025 = os.path.realpath(SCRIPTDIR + "/../InnerSphereMap_data\IS3025")
systems_3040 = os.path.realpath(SCRIPTDIR + "/../InnerSphereMap_data\IS3040")
systems_3063 = os.path.realpath(SCRIPTDIR + "/../InnerSphereMap_data\IS3063")

def enumerate_itemCollections(path):
    """Enumerate the item collection CSVs at path"""
    collections = []
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if filename.endswith(".csv"):
            collections.append(filename.replace(".csv",""))
    return collections
    

def get_system_tags(sysdef):
    """Return an array of planet_* tags"""
    return sysdef['Tags']['items']

def get_system_owner(sysdef):
    """Return an array of planet_* tags"""
    return sysdef['ownerID']

def get_system_distance(sysdef1, sysdef2):
    my_x = sysdef1["Position"]["x"]
    my_y = sysdef1["Position"]["y"]
    their_x =  sysdef2["Position"]["x"]
    their_y = sysdef2["Position"]["y"]
    distance = math.sqrt((their_x - my_x)**2 + (their_y - my_y)**2)
    return distance

def get_nearby_systems(sysdef, all_systems, distance_cutoff, count=sys.maxsize):
    systems = []
    for target in all_systems.values():
        distance = get_system_distance(sysdef, target)
        if distance <= distance_cutoff and target != sysdef:
            systems.append(target)
    
    systems = systems[0:count]
    return systems

def set_planet_faction_tag(sysdef):
    owner = get_system_owner(sysdef)
    # Fix some one-off exceptions
    if owner == "TaurianConcordat":
        owner = "taurian"
    elif owner == "AuriganDirectorate":
        owner = "directorate"
    elif owner == "MagistracyOfCanopus":
        owner = "magistracy"
    elif owner == "AuriganRestoration":
        owner = "restoration"
    faction_tag = 'planet_faction_' + owner.lower()
    sysdef['Tags']['items'].append(faction_tag)
    return faction_tag

def get_faction_shop_collections(itemCollections, sysdef):
        owner = get_system_owner(sysdef)
        system_tags = get_system_tags(sysdef)
        #system_parts = system_tags.split('_')
        faction_collections = []

        if ('planet_industry_manufacturing' in system_tags and 'planet_industry_mining' in system_tags):
            for collection in itemCollections:
                collection_parts = list(set(collection.split('_')))
                if owner in collection_parts and 'faction' in collection_parts:
                    faction_collections.append(collection)
        return faction_collections

        

def get_system_shop_collections(itemCollections, sysdef):
    """
    Determine appropriate shop item collections.
    
    This function errs to being very generous.
    """
    system_tags = get_system_tags(sysdef)
    system_desc = sysdef['Description']['Details']
    owner = get_system_owner(sysdef)
    system_collections = []

    for system_tag in system_tags:
        # Split the item tags by underscore.
        system_parts = system_tag.split('_')
        # If a particular part is about 'none' then we don't care about it
        # if 'none' in system_parts:
        #    continue
        for collection in itemCollections:
            # Split the item collection possibilities by underscore
            collection_parts = list(set(collection.split('_')))
            # If it's not a shop-type collection, we move along
            if (('shop' not in collection_parts) and
               ('major' not in collection_parts) and
               ('minor' not in collection_parts)):
                continue
            # Skip all reward collections
            if ('Reward' in collection_parts):
                continue
            # Only show "major" faction items on large population worlds
            if ('major' in collection_parts and 'planet_pop_large' not in system_tags):
                continue
            # Only show "minor" faction items on medium population worlds
            if ('minor' in collection_parts and 'planet_pop_medium' not in system_tags):
                continue

            for part in list(set(system_parts)):
                # Populate Regular Shops
                if ((part in collection_parts) or
                    (part + 'Progression' in collection_parts and 'planet_civ_innersphere' in system_tags)):
                    system_collections.append(collection)

                # ISM doesn't have the following tags, so we use some stand ins
                if ('agriculture' == part):
                    part = "chemicals"
                if ('aquaculture' == part):
                    part = 'chemicals'
                if ('ruins' == part):
                    part = 'battlefield'
                if ('innersphere' == part):
                    part = 'electronics'
                if ('manufacturing' == part and 'planet_industry_mining' in system_tags):
                    part = 'industrial'
                
                if ((part in collection_parts) or
                    (part + 'Progression' in collection_parts and 'planet_civ_innersphere' in system_tags)):
                    system_collections.append(collection)
    
    if len(system_collections) == 0:
        # Empty shops are depressing and most systems are abandoned.
        system_collections.append('itemCollection_table_AdditionalLoot_common')
    system_collections=list(set(system_collections))
    print(system_collections)
    return system_collections
        
def export_StarSystem(filepath, sysdef):
     with io.open(filepath, "w", encoding='utf8') as sysjson:
         sysjson.write(json.dumps(sysdef, sort_keys=True, indent=4))

def get_system_difficulty(sysdef, all_systems, base_diff = 1):
    system_difficulty=base_diff
    for t in DIFFICULTY_MODS:
        if t in get_system_tags(sysdef):
            system_difficulty += DIFFICULTY_MODS[t]
            
    closest = get_nearby_systems(sysdef, all_systems, 30)
    print(closest)
    for s in closest:
        if get_system_owner(s) == "NoFaction" or get_system_owner(sysdef) == "NoFaction":
            continue
        if get_system_owner(s) != get_system_owner(sysdef) and system_difficulty < 9:
            system_difficulty += 1
        if get_system_owner(s) == get_system_owner(sysdef) and system_difficulty > 2 :
            system_difficulty -= .25
            
            
    system_difficulty = max(STD_DIFF, system_difficulty)
    system_difficulty = min(10, system_difficulty)
    if system_difficulty > 10:
        system_difficulty = int(math.floor(system_difficulty))
    elif system_difficulty > 1 and system_difficulty < 2:
        system_difficulty = int(math.ceil(system_difficulty))
    else:
        system_difficulty = int(round(system_difficulty))
    
            
    # else:
    #     system_difficulty = int(round(system_difficulty))
    
     #if system_difficulty < 5:
     #    system_difficulty = int(round(system_difficulty+random.lognormvariate(0,STD_DEV)))
     #elif system_difficulty < 10:
     #    system_difficulty = int(round(system_difficulty-random.lognormvariate(0,STD_DEV)))
    
     #if system_difficulty <= STD_DEV:
     #    system_difficulty = int(round(system_difficulty+random.paretovariate(STD_DEV)))
     #else:
     #    system_difficulty = int(round(random.gauss(system_difficulty, STD_DEV)))
    if system_difficulty < 1:
        system_difficulty = 1
    elif system_difficulty > 10:
        system_difficulty = 10
    print(system_difficulty)
    return system_difficulty

def get_map_params(all_systems, map_size=550):
        min_x = 0
        min_y = 0
        max_x = 0
        max_y = 0
        ly_per_coord = 0
        for target in all_systems.values():
            if target["Position"]["x"] < min_x:
                min_x = target["Position"]["x"]
            if target["Position"]["x"] > max_x:
                max_x = target["Position"]["x"]
                
            if target["Position"]["y"] < min_x:
                min_y = target["Position"]["y"]
            if target["Position"]["y"] > max_x:
                max_y = target["Position"]["y"]
                
        ly_per_coord = min(map_size/(max_x - min_x),
                                map_size/(max_y - min_y))
        map_params = { 'min_x': min_x, 'max_x': max_x,
                 'min_y': min_x, 'max_y': max_x,
                 'ly_per_coord': ly_per_coord
                }
        #print(map_params)
        return map_params

def get_jump_distance(sysdef, all_systems, max_jump=30, map_size=550):
    '''
    

    Parameters
    ----------
    sysdef : dict
        System definition dictionatry.
    all_systems : dict(dict())
        A dictionary of all the systems.
    max_jump : int, optional
        What is the longest possible jump? The default is 30.
    map_size : int, optional
        How many lightyears is the area covered by the map. The default is 550.

    Returns
    -------
    Jump distance.

    '''
    closest = get_nearby_systems(sysdef, all_systems, max_jump)
    print("Closest:", closest)
    distances = [get_system_distance(sysdef, i) for i in closest]
    if len(distances) == 0:
        distance = max_jump
    else:
        distance = statistics.harmonic_mean(distances)
    jump_distance = distance #* map_params['ly_per_coord']
    print('Jump distance: ' + str(jump_distance))
    if jump_distance > max_jump:
        return int(max_jump)
    else:
        return int(jump_distance)
        
    
def get_systems_dict(systems_dir):
    sysdefs = {}
    with pushd(systems_dir):
        # Enumerate the era directory
        directory = os.fsencode(systems_dir)
        # Iterate over the directories in the era
        for d in os.listdir(directory):
            # Get the nested faction directory
            faction_dir = d
            print("Faction: " , faction_dir.decode("utf-8") )
            for filename in os.listdir(faction_dir):
                filename = os.fsdecode(filename)
                if filename.endswith(".json"):
                    filepath=os.path.join(str(systems_3025),
                                          str(faction_dir.decode("utf-8") ),
                                          str(filename))
                    print(str(filepath))
                    with io.open(filepath, "r", encoding='utf8') as sysjson:
                        sysdef = sysjson.read()
                        sysdef = json.loads(sysdef)
                        sysdefs[sysdef['CoreSystemID']] = sysdef
    return sysdefs
                        

print(enumerate_itemCollections(VANILLA_ITEMCOLLECTION_DEFS))


i=1
alltags = []
print(systems_3025)
# Change to the era directory
difficulty_distribution={}
STD_DEV=5
STD_DIFF=1
sysdefs = get_systems_dict(systems_3025)
print(len(sysdefs))
#sys.exit(0)
for (syscoreid, sysdef) in sysdefs.items():
    set_planet_faction_tag(sysdef)
    alltags += get_system_tags(sysdef)
    system_difficulty=get_system_difficulty(sysdef, sysdefs)
    
    if system_difficulty not in difficulty_distribution:
        difficulty_distribution[system_difficulty] = 1
    difficulty_distribution[system_difficulty] += 1
    
    sysdef['JumpDistance'] = get_jump_distance(sysdef, sysdefs)
    sysdef['DefaultDifficulty'] = system_difficulty
    itemCollections = enumerate_itemCollections(VANILLA_ITEMCOLLECTION_DEFS)
    sysdef['SystemShopItems'] = get_system_shop_collections(itemCollections,
                                        sysdef)
    sysdef['FactionShopItems'] = get_faction_shop_collections(itemCollections,
                                                              sysdef)
    if len(sysdef['FactionShopItems']) == 0:
        sysdef['factionShopOwnerID'] = "INVALID_UNSET"
    else:
        sysdef['factionShopOwnerID'] = get_system_owner(sysdef)
    os.makedirs(os.path.join(SCRIPTDIR, "IS3025", "StarSystems"), exist_ok = True)
    export_StarSystem(os.path.join(SCRIPTDIR, "IS3025", "StarSystems", sysdef['CoreSystemID']+'.json'), sysdef)
    #print(json.dumps(sysdef, sort_keys=True, indent=4))
    i += 1
    print(syscoreid, i)


print(OrderedDict(sorted(difficulty_distribution.items())))