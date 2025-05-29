import geo_mapper_api.converters as gma
import geo_mapper_api.filters as filters
import osmnx as ox
import geopandas as gpd
import pandas as pd

import concurrent.futures

def process_county(csv_path, inrix_df, county_name, threshold_distance=25.0):
    try:
        # Load and filter INRIX data
        tdf = inrix_df.loc[inrix_df["County"].isin([county_name])]
        tdf = tdf.copy(deep=True)
        polygon = gma.get_exterior_polygon(tdf)
        # Get OSM graph
        polygon= gma.get_exterior_polygon(tdf)
        G = gma.get_osm_graph(polygon, filters.base_filter)
        # Get nodes and edges
        nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
        # Prepare OSMNX INRIX data
        haywood_osm = gma.prepare_osmnx_inrix_data(csv_path, tdf)
        # Merge and filter INRIX and OSM data
        merged_osm_inrix = gma.merge_and_filter_inrix_osm(edges, haywood_osm, tdf)

        # Apply bearing classification
        merged_osm_inrix  = gma.apply_bearing_classification(merged_osm_inrix)

        # Filter groups by match
        filtered_osm_inrix, unfiltered__osm_inrix = gma.filter_groups_by_match(merged_osm_inrix)
        # Plot the results
        gma.plot_matched_geometry(filtered_osm_inrix ,'geometry_osm', 'Matched Geometry ')
        gma.plot_matched_geometry(merged_osm_inrix, 'geometry_inrix', 'Inrix Geometry ')
        gma.plot_matched_geometry(edges, 'geometry', 'OSM Geometry ')

        # Group by 'u', 'v', and 'geometry'
        grouped = filtered_osm_inrix.groupby(['u', 'v','key'])

        # Process the top groups and find overlapping geometries
        all_overlapping_geometries = gma.process_top_groups(grouped, nodes)

        # Reproject both geometry columns to a metric CRS (e.g., EPSG 3857 for Web Mercator)
        merged_osm_inrix = gpd.GeoDataFrame(all_overlapping_geometries.copy(),geometry='geometry')
        merged_osm_inrix = gma.reproject_geometry(merged_osm_inrix, 'geometry')
        merged_osm_inrix = gma.reproject_geometry(merged_osm_inrix, 'geometry_inrix')

        # Define the acceptable threshold distance in meters
        threshold_distance = 25.0  # 5 meters

        # Calculate and check distances
        proximity_results = gma.check_osm_inrix_proximity(merged_osm_inrix, threshold_distance)

        # outliers = proximity_results[~proximity_results['within_threshold']]

        prox = proximity_results[proximity_results['within_threshold']]
        prox['county'] = county_name  # Add county name to results
        print(county_name)
        print(prox.shape)
        return prox

    except Exception as e:
        print(f"Error processing {county_name}: {e}")
        return pd.DataFrame()  # Return empty DataFrame on failure


def parallel(geojson_path, csv_path, counties, threshold_distance):
    all_results = []

    all_counties_df = gma.load_and_prepare_inrix_data_for_multiple_counties(geojson_path, counties)
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(process_county, csv_path, all_counties_df, county, threshold_distance): county
            for county in counties
        }

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if not result.empty:
                all_results.append(result)

    if all_results:
        return pd.concat(all_results, ignore_index=True)
    else:
        print("No results returned.")
        return pd.DataFrame()


def serial(geojson_path, csv_path, counties, threshold_distance):

    if isinstance(counties, str):
        counties = [counties]
    all_results = []

    all_counties_df = gma.load_and_prepare_inrix_data_for_multiple_counties(geojson_path, counties)
    
    for county_name in counties:
        print(f"Processing county: {county_name}")
        # Load and filter INRIX data
        prox = process_county(csv_path, all_counties_df, county_name, threshold_distance)
        all_results.append(prox)

    all_results = pd.concat(all_results, ignore_index=True)
    return all_results
