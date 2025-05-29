import pandas as pd
import geopandas as gpd
import numpy as np
import osmnx as ox
import math
import warnings

warnings.filterwarnings("ignore")

custom_filter = ('["highway"!~"cycleway|footway|path|pedestrian|'
                    'steps|service|track|construction|bridleway|'
                    'corridor|elevator|escalator|proposed|'
                    'rest_area|escape|emergency_bay|bus_guideway"]')

def load_and_prepare_inrix_data(geojson_path, county_name):
    """Load and filter INRIX GeoDataFrame based on the specified county."""
    inrix_df = gpd.read_file(geojson_path)
    inrix_df.replace(to_replace='', value=np.nan, inplace=True)
    filtered_df = inrix_df.loc[inrix_df["County"].isin([county_name])]
    filtered_df["PreviousXD"] = pd.to_numeric(filtered_df["PreviousXD"], errors='coerce')
    filtered_df["XDSegID"] = pd.to_numeric(filtered_df["XDSegID"], errors='coerce')
    filtered_df["NextXDSegI"] = pd.to_numeric(filtered_df["NextXDSegI"], errors='coerce')
    return filtered_df

def load_and_prepare_inrix_data_for_multiple_counties(geojson_path, county_names):
    if isinstance(county_names, str):
        county_names = [county_names]
    """Load and filter INRIX GeoDataFrame based on the specified counties."""
    inrix_df = gpd.read_file(geojson_path, engine="fiona")
    inrix_df.replace(to_replace='', value=np.nan, inplace=True)
    filtered_df = inrix_df.loc[inrix_df["County"].isin(county_names)]
    filtered_df["PreviousXD"] = pd.to_numeric(filtered_df["PreviousXD"], errors='coerce')
    filtered_df["XDSegID"] = pd.to_numeric(filtered_df["XDSegID"], errors='coerce')
    filtered_df["NextXDSegI"] = pd.to_numeric(filtered_df["NextXDSegI"], errors='coerce')
    return filtered_df

def get_exterior_polygon(geodf):
    """
    Get the exterior polygon of a GeoDataFrame containing multiple LineStrings.
    
    Parameters:
    geodf (GeoDataFrame): The GeoDataFrame containing the geometries.
    
    Returns:
    shapely.geometry.Polygon: The exterior polygon of the combined geometries.
    """
    # Combine all the geometries into a single geometry (union)
    combined_geom = geodf.unary_union
    
    # Get the convex hull of the combined geometry to form an exterior polygon
    exterior_polygon = combined_geom.convex_hull
    
    return exterior_polygon

def get_osm_graph(polygon, custom_filter):
    """
    Get OSM road network graph for the given polygon with the custom filter.
    
    Parameters:
    polygon (shapely.geometry.Polygon): The polygon defining the area of interest.
    custom_filter (str): Custom filter to apply to the OSM data.
    
    Returns:
    networkx.MultiDiGraph: The road network graph for the given polygon.
    """
    G = ox.graph_from_polygon(polygon, custom_filter=custom_filter, network_type='drive')
    return G

def classify_bearing(bearing):
    if bearing >= 337.5 or bearing < 22.5:
        return 'N'
    elif 22.5 <= bearing < 67.5:
        return 'NE'
    elif 67.5 <= bearing < 112.5:
        return 'E'
    elif 112.5 <= bearing < 157.5:
        return 'SE'
    elif 157.5 <= bearing < 202.5:
        return 'S'
    elif 202.5 <= bearing < 247.5:
        return 'SW'
    elif 247.5 <= bearing < 292.5:
        return 'W'
    elif 292.5 <= bearing < 337.5:
        return 'NW'
    

def calculate_bearing(point1, point2):
    lon1, lat1 = point1
    lon2, lat2 = point2
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    x = math.sin(dLon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dLon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing

def line_bearing(line):
    point1 = (line.coords[0][0], line.coords[0][1])
    point2 = (line.coords[-1][0], line.coords[-1][1])
    return calculate_bearing(point1, point2)
    

def prepare_osmnx_inrix_data(csv_path, davidson_inrix_df):
    """Prepare and expand OSMNX INRIX data."""
    osmnx_inrix = pd.read_csv(csv_path)
    Ave_21 = osmnx_inrix[osmnx_inrix.XDSegID.isin(davidson_inrix_df['XDSegID'])].reset_index(drop=True)
    Ave_21['OSMWayIDs'] = Ave_21['OSMWayIDs'].apply(lambda x: x.split(';'))
    Ave_21['OSMWayDirections'] = Ave_21['OSMWayDirections'].apply(lambda x: x.split(';'))
    Ave_21_expanded = Ave_21.explode(['OSMWayIDs', 'OSMWayDirections']).explode('OSMWayDirections')
    Ave_21_expanded['OSMWayIDs'] = pd.to_numeric(Ave_21_expanded['OSMWayIDs'], errors='coerce')
    return Ave_21_expanded

def merge_and_filter_inrix_osm(edges, Ave_21_expanded, davidson_inrix_df):
    """Merge and filter INRIX and OSM data."""
    test = edges.reset_index().explode('osmid').sort_values(by='osmid', ascending=False).merge(
        Ave_21_expanded, left_on='osmid', right_on='OSMWayIDs', how='inner')
    test_inrix = test[['u', 'v','key', 'osmid', 'lanes', 'name', 'highway', 'oneway', 'reversed', 'length',
                       'geometry', 'XDSegID', 'OSMWayDirections']].merge(davidson_inrix_df,
                                                                       left_on='XDSegID', right_on='XDSegID', how='inner',suffixes=('_osm', '_inrix'))
    return test_inrix

def apply_bearing_classification(df):
    """Apply bearing calculation and classification."""
    df['osm_line_bearing'] = df['geometry_osm'].apply(line_bearing)
    df['compass_direction'] = df['osm_line_bearing'].apply(classify_bearing)
    df['match'] = df.apply(lambda row: row['Bearing'] in row['compass_direction'], axis=1)
    return df

def filter_groups_by_match(test_inrix):
    """Group and filter INRIX data based on match."""
    grouped = test_inrix.groupby(['osmid', 'XDSegID'])
    filtered_groups = []
    unfiltered_groups = []
    for _, group in grouped:
        if len(group) == 1:
            filtered_groups.append(group)
        else:
            filtered_groups.append(group[group['match'] == True])
            unfiltered_groups.append(group[group['match'] == False])
    filtered_inrix = pd.concat(filtered_groups)
    unfiltered_inrix = pd.concat(unfiltered_groups)
    return filtered_inrix, unfiltered_inrix


def buffer_geometries(gdf, column_name, buffer_size):
    """
    Applies a buffer to the geometries in a GeoDataFrame.
    
    Parameters:
    - gdf: GeoDataFrame containing the geometries.
    - column_name: The name of the geometry column to buffer.
    - buffer_size: The buffer size to apply.
    
    Returns:
    - GeoDataFrame with buffered geometries.
    """
    buffered_gdf = gdf.copy()
    buffered_gdf[column_name] = buffered_gdf[column_name].buffer(buffer_size)
    return buffered_gdf

def find_overlapping_geometries(group_df,gdf_osm, gdf_inrix, gdf_nodes):
    """
    Finds overlapping geometries between OSM, INRIX, and nodes data.
    
    Parameters:
    - gdf_osm: GeoDataFrame containing OSM data.
    - gdf_inrix: GeoDataFrame containing INRIX data.
    - gdf_nodes: GeoDataFrame containing nodes data.
    
    Returns:
    - DataFrame of overlapping geometries.
    """
    buffered_gdf_osm = buffer_geometries(gdf_osm, 'geometry', 1e-4)
    buffered_gdf_inrix = buffer_geometries(gdf_inrix, 'geometry_inrix_copy', 1e-6)
    buffered_gdf_nodes = buffer_geometries(gdf_nodes, 'geometry', 1e-3)

    overlapping_nodes = gpd.sjoin(buffered_gdf_nodes, buffered_gdf_inrix, how='inner', predicate='intersects')
    
    if len(overlapping_nodes) == 0:
        buffered_gdf_inrix = buffer_geometries(gdf_inrix, 'geometry_inrix_copy', 1e-4)
        overlapping_nodes = gpd.sjoin(buffered_gdf_osm, buffered_gdf_inrix, how='inner', predicate='intersects')
        overlapping_nodes = overlapping_nodes[['u', 'v','key', 'osmid', 'XDSegID', 'geometry', 'geometry_inrix', 'osm_line_bearing', 'Bearing', 'compass_direction']].drop_duplicates().reset_index(drop=True)
        overlapping_nodes = group_df[group_df.XDSegID.isin(overlapping_nodes.XDSegID)][['u', 'v','key', 'osmid', 'XDSegID', 'geometry', 'geometry_inrix', 'osm_line_bearing', 'Bearing', 'compass_direction']].drop_duplicates().reset_index(drop=True)
    else:
        overlapping_nodes = overlapping_nodes.drop_duplicates().reset_index(drop=True)
        overlapping_nodes = pd.merge(overlapping_nodes[['osmid', 'XDSegID']], overlapping_nodes[['osmid', 'XDSegID']], on='XDSegID', how='inner', suffixes=('_u', '_v'))
        overlapping_nodes = overlapping_nodes[(overlapping_nodes['osmid_u'] != overlapping_nodes['osmid_v'])]
        
        
        if len(overlapping_nodes) == 0:
            buffered_gdf_inrix = buffer_geometries(gdf_inrix, 'geometry_inrix_copy', 1e-4)
            overlapping_nodes = gpd.sjoin(buffered_gdf_osm, buffered_gdf_inrix, how='inner', predicate='intersects')
            overlapping_nodes = overlapping_nodes[['u', 'v','key', 'osmid', 'XDSegID', 'geometry', 'geometry_inrix', 'osm_line_bearing', 'Bearing', 'compass_direction']].drop_duplicates().reset_index(drop=True)
            overlapping_nodes = group_df[group_df.XDSegID.isin(overlapping_nodes.XDSegID)][['u', 'v','key', 'osmid', 'XDSegID', 'geometry', 'geometry_inrix', 'osm_line_bearing', 'Bearing', 'compass_direction']].drop_duplicates().reset_index(drop=True)
        else:
            overlapping_nodes = group_df[group_df.XDSegID.isin(overlapping_nodes.XDSegID)][['u', 'v','key', 'osmid', 'XDSegID', 'geometry', 'geometry_inrix', 'osm_line_bearing', 'Bearing', 'compass_direction']].drop_duplicates().reset_index(drop=True)
    
    return overlapping_nodes

def process_top_groups(grouped_data, nodes):
    """
    Processes the top groups and finds overlapping geometries.
    
    Parameters:
    - grouped_data: Grouped DataFrame containing the top groups.
    - nodes: GeoDataFrame containing nodes data.
    
    Returns:
    - Concatenated DataFrame of all overlapping geometries.
    """
    all_overlapping_geometries = []
    
    for group_name, group_df in grouped_data:
        gdf_osm = gpd.GeoDataFrame(group_df.drop(columns=['XDSegID', 'geometry_inrix'], axis=1), geometry='geometry')
        gdf_inrix = gpd.GeoDataFrame(group_df[['XDSegID', 'geometry_inrix']], geometry='geometry_inrix')
        gdf_inrix['geometry_inrix_copy'] = gdf_inrix['geometry_inrix']
        gdf_inrix.set_geometry('geometry_inrix_copy', inplace=True)
        gdf_nodes = gpd.GeoDataFrame(nodes[nodes.index.isin([group_name[0], group_name[1]])].reset_index(), geometry='geometry')
        
        overlapping_geometries = find_overlapping_geometries(group_df,gdf_osm, gdf_inrix, gdf_nodes)
        all_overlapping_geometries.append(overlapping_geometries)
    
    return pd.concat(all_overlapping_geometries, ignore_index=True)

def reproject_geometry(gdf, geom_column, target_crs="EPSG:3857"):
    """
    Reproject a specific geometry column in a GeoDataFrame to a coordinate system using meters.
    
    Parameters:
    - gdf: The input GeoDataFrame with CRS 4326.
    - geom_column: The name of the geometry column to reproject.
    - target_crs: The target CRS for the projection (default is EPSG 3857).
    
    Returns:
    - GeoDataFrame: The GeoDataFrame with the specified geometry column reprojected.
    """
    gdf = gdf.copy()
    gdf = gdf.set_geometry(geom_column).to_crs(target_crs)
    return gdf

def plot_matched_geometry(df, geometry_column, title):
    """Plot the matched geometries with map tiles using contextily."""
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries(df[geometry_column]))
    gdf = gdf.to_crs(epsg=3857)

def calculate_nearest_distance(osm_geom, inrix_geom):
    """
    Calculate the nearest distance between an OSM edge and an INRIX segment.
    
    Parameters:
    - osm_geom: Geometry of the OSM edge (LineString).
    - inrix_geom: Geometry of the INRIX segment (LineString).
    
    Returns:
    - float: The minimum distance between the OSM edge and the INRIX segment.
    """
    return osm_geom.distance(inrix_geom)

def check_osm_inrix_proximity(test_data, threshold):
    """
    Check the proximity of OSM edges to their mapped INRIX segments.
    
    Parameters:
    - test_data: DataFrame containing OSM edges and mapped INRIX segments.
    - threshold: Maximum acceptable distance between OSM edge and INRIX segment in meters.
    
    Returns:
    - DataFrame: Results with calculated distances and match status.
    """
    results = []

    for index, row in test_data.iterrows():
        osm_geom = row['geometry']
        inrix_geom = row['geometry_inrix']

        # Calculate the nearest distance between the OSM edge and INRIX segment
        distance = calculate_nearest_distance(osm_geom, inrix_geom)
        
        # Check if the distance is within the acceptable threshold
        is_within_threshold = distance <= threshold

        results.append({
            'u': row['u'],
            'v': row['v'],
            'key': row['key'],
            'osmid': row['osmid'],
            'XDSegID': row['XDSegID'],
            'osm_geom': osm_geom,
            'inrix_geom': inrix_geom,
            'distance': distance,
            'within_threshold': is_within_threshold
        })

    return pd.DataFrame(results)

