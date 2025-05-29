# Setup
This requires `python>=3.9` but pretty specific versions of packages. If this fails, try to create a new virtual environment with python 3.9 specifically for this package.
```
pip install geospatial_mapper
```

# Requirements
It needs both the `OSMConflation` and `GeoJSON` data for the target area. You can obtain both from Inrix [Data Download Service](https://docs.inrix.com/datadownload/datadownload/) provided you have an access token or login credentials.

This conflation `csv` should have the following features:
| Feature                 | Type    | Example   |
| ----------------------- | ------- | --------- |
| XDSegID                 | Integer | 136894283 |
| OSMWayIDs               | Integer | 19659968  |
| OSMWayDirections        | String  | N         |
| WayStartOffset\_m       | Float   | 1077.78   |
| WayEndOffset\_m         | Float   | 1851.31   |
| WayStartOffset\_percent | Float   | 33.706    |
| WayEndOffset\_percent   | Float   | 57.897    |

While the `geojson` data should have the following features:
| Feature    | Type     | Example            |
| ---------- | -------- | ------------------ |
| OID        | Integer  | 7931440            |
| XDSegID    | Integer  | 156418860          |
| PreviousXD | Float    | nan                |
| NextXDSegI | Float    | 395960459.0        |
| FRC        | Integer  | 4                  |
| RoadNumber | Float    | nan                |
| RoadName   | String   | DRHESSRD           |
| LinearID   | Float    | nan                |
| Country    | String   | UNITEDSTATES       |
| State      | String   | TENNESSEE          |
| County     | String   | HAYWOOD            |
| District   | Float    | nan                |
| PostalCode | String   | 38006              |
| Miles      | Float    | 0.5902665205613952 |
| Lanes      | Float    | 1.0                |
| SlipRoad   | Integer  | 0                  |
| SpecialRoa | Float    | nan                |
| RoadList   | String   | DRHESSRD           |
| StartLat   | Float    | 35.67248           |
| StartLong  | Float    | -89.14147          |
| EndLat     | Float    | 35.666218484838986 |
| EndLong    | Float    | -89.13571015096953 |
| Bearing    | String   | S                  |
| XDGroup    | Integer  | 2013963            |
| ShapeSRID  | Integer  | 4326               |
| geometry   | Geometry | LINESTRING         |


# Usage

```bash
  DATA_DIR = "./tests/data"
  geojson_path = os.path.join(DATA_DIR, 'test.geojson')
  csv_path = os.path.join(DATA_DIR, 'test.csv')
  county_name = ['CROCKETT']
  df = parallel(geojson_path, csv_path, county_name, threshold_distance=25)
```

# Development
Test data might be proprietary but these are just the maprelease data from Inrix.
Please the csv and geojson in the `tests/data` folder and name them `test.csv` and `test.geojson`. Pytest should succeed.