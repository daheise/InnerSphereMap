import os
import io
import sys
from os import chdir, getcwd
from os.path import realpath
import json

SCRIPTDIR=os.path.dirname(os.path.realpath(__file__))
# Assume Steam
BATTLETECH_INSTALL_DIR=os.path.realpath("C:\Program Files (x86)\Steam\steamapps\common\BATTLETECH")
VANILLA_ITEMCOLLECTION_DEFS=os.path.realpath("C:\Program Files (x86)\Steam\steamapps\common\BATTLETECH\BattleTech_Data\StreamingAssets\data\itemCollections")

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
        

print(enumerate_itemCollections(VANILLA_ITEMCOLLECTION_DEFS))


i=1
print(systems_3025)
# Change to the era directory
with pushd(systems_3025):
    # Enumerate the era directory
    directory = os.fsencode(systems_3025)
    # Iterate over the directories in the era
    for dir in os.listdir(directory):
        # Get the nested faction directory
        faction_dir = dir
        print(faction_dir.decode("utf-8") )
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
                    set_planet_faction_tag(sysdef)
                    print(get_system_tags(sysdef))
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
                    export_StarSystem(os.path.join(SCRIPTDIR, "IS3025", "StarSystems", filename), sysdef)
                    #print(json.dumps(sysdef, sort_keys=True, indent=4))
                    i += 1
                    print(i)