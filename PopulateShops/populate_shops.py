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
    return sysdef['Tags']['items']

def get_system_collections(itemCollections, system_tags, system_desc, owner = None):
    """
    Determine appropriate shop item collections.
    
    This function errs to being very generous.
    """
    system_collections = []
    for system_tag in system_tags:
        # Split the item tags by underscore.
        system_parts = system_tag.split('_')
        # If a particular part is about 'none' then we don't care about it
        if 'none' in system_parts:
            continue
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
            # ISM doesn't have chemical tags; use agriculture as a stand in
            if ('agriculture' in system_parts):
                system_parts.append('chemicals')
            if ('ruins' in system_parts):
                system_parts.append('battlefield')
            if ('industry' in system_parts and 'rich' in system_parts):
                system_parts.append('industrial')
            if ('industry' in system_parts and ('rich' in system_parts or 'poor' in system_parts)):
                system_parts.append('electronics')
            for part in list(set(system_parts)):
                if ((part in collection_parts) or
                    (part + 'Progression' in collection_parts)):
                #if any(item in collection_parts for item in system_parts):
                    print(collection)
                    system_collections.append(collection)
    system_collections.append('itemCollection_shop_progression_med')
    system_collections=list(set(system_collections))
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
                    print(get_system_tags(sysdef))
                    sysdef['SystemShopItems'] = []
                    shopsToAdd = get_system_collections(enumerate_itemCollections(VANILLA_ITEMCOLLECTION_DEFS),
                                                        get_system_tags(sysdef),
                                                        sysdef['Description']['Details'])
                    for item in  shopsToAdd:
                        sysdef['SystemShopItems'].append(item)
                    os.makedirs(os.path.join(SCRIPTDIR, "IS3025", "StarSystems"), exist_ok = True)
                    export_StarSystem(os.path.join(SCRIPTDIR, "IS3025", "StarSystems", filename), sysdef)
                    #print(json.dumps(sysdef, sort_keys=True, indent=4))
                    i += 1
                    print(i)