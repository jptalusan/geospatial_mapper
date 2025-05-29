from geo_mapper_api.inrix_to_osm import parallel
import os

def test_parallel():
    print("Running inrix to osm mapping...")
    DATA_DIR = "./tests/data"
    geojson_path = os.path.join(DATA_DIR, 'test.geojson')
    csv_path = os.path.join(DATA_DIR, 'test.csv')
    county_name = ['CROCKETT']
    df = parallel(geojson_path, csv_path, county_name, threshold_distance=25)
    assert not df.empty, "DataFrame should not be empty"
    assert df.county.unique()[0] == 'CROCKETT', "County name should be CROCKETT"