import fire
import string
from inventree.api import InvenTreeAPI
import yaml
from inventree.stock import StockLocation
import pandas as pd
from pathvalidate import sanitize_filename

SERVER_ADDRESS = 'http://JASPER-PC:1337'
TOKEN = 'd46f046920878a12812243e7127748f6f3f1d42d'

class Application:
    def __init__(self, address, token):
        self.address = address
        self.token = token

    def _connect(self):
        print(f"Connecting to server {self.address}")
        api = InvenTreeAPI(self.address, token=self.token)
        print("Connection OK")
        return api

    def _get_unique_name(self, api, name):
        idx = 0
        locations = StockLocation.list(api)
        location_names = [l.name for l in locations]
        while True:
            full_name = f"{name} {idx}"
            if full_name not in location_names:
                return full_name
            idx += 1

    def add(self, filename):
        api = self._connect()
        with open(filename, "r") as f:
            config = yaml.safe_load(f)
        meta = config.pop("meta")
        grids = config.pop("grids")
        print(f"Adding new {filename}")
        name = meta["name"]
        description = meta.get("description", "")
        print(f"Default name is {name}")
        full_name = self._get_unique_name(api, name)
        print(f"Creating location {full_name}")
        new_location = StockLocation.create(api, {
            "name": full_name,
            "description": description,
            "parent": ""
        })
        for key, vals in grids.items():
            print(f"Creating locations for grid {key}")
            rows = vals.get("rows", 1)
            cols = vals.get("columns", 1)
            prefix = vals.get("prefix", "")
            for r in range(rows):
                r = string.ascii_uppercase[r]
                for c in range(cols):
                    name = f"{prefix}{r}{c}"
                    bin = StockLocation.create(api, {
                        "name": name,
                        "parent": new_location.pk
                    })
                    print(f"Created location {bin.pathstring}")


    def _delete(self, api, location):
        for l in location.getChildLocations():
            self._delete(api, l)
        print(f"Deleting {location.pathstring}")
        location.delete()

    def _get_location(self, api, id):
        location = StockLocation(api, pk=id)
        if not location.pk:
            print(f"Error: location not found")
            exit(1)
        return location

    def delete(self, id):
        api = self._connect()
        print(f"Deleting location with ID {id}")
        location = self._get_location(api, id)
        print(f'WARNING: DELETING ALL LOCATIONS UNDER "{location.pathstring}"')
        confirm = input(f'Type "{location.name}" to confirm: ')
        if confirm != location.name:
            print("Not deleting")
            exit(1)
        self._delete(api, location)

    @staticmethod
    def _qr_data(id):
        return f'{{"stocklocation": {id}}}'

    def _get(self, location):
        name = location.name
        id = location.pk
        print(f"Creating location entry {name} with ID {id}")
        df = pd.DataFrame(
            [[name, self._qr_data(id)]],
            columns=["name", "qr_data"], index=None)
        for l in location.getChildLocations():
            df = pd.concat([df, self._get(l)])
        return df

    def get(self, id, export_type="csv"):
        api = self._connect()
        print(f"Getting location with ID {id}")
        location = self._get_location(api, id)
        df = self._get(location)
        if export_type == "csv":
            filename = sanitize_filename(f"{location.name}.csv")
            print(f"Saving table to {filename}")
            df.to_csv(filename, index=False)
        else:
            print(f"Error: unknown export type {export_type}")

    def export(self):
        api = self._connect()
        import pdb;pdb.set_trace()


if __name__ == "__main__":
    fire.Fire(Application)