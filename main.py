import streamlit as st
import pandas as pd
import folium
import os
from streamlit_folium import st_folium, folium_static
from ckanapi import RemoteCKAN
from dotenv import load_dotenv
import requests


load_dotenv('.env')

st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 0rem;
                    padding-right: 0rem;
                    margin-bottom: 0rem;
                    margin-left: 0rem;
                    margin-right: 0rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 500px !important; # Set the width to your desired value
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def create_map():
    ## what if we preloaded the datasets that we already have? 
    ## Add them here so the map is initialized with the datasets

    map = folium.Map(location=[37.1661, -119.44944], zoom_start=4)      
    return map

if 'map' not in st.session_state:    
    map = create_map()
    st.session_state.map = map

def fetch_raster(dataset):
    dataset_name = dataset['title']
    url = dataset

def get_geojson(resource):
    url = resource['url']    
    print("url")
    print(url)
    geojson = requests.get(url).json()
    return geojson

def get_opentopo_geojson(url):
    information = requests.get(url).json()

    json_link = [x['href'] for x in information['links'] if x['rel'] == 'child' and 'raster' not in x['href']]
    if len(json_link) > 0:
        geojson = requests.get(json_link[0]).json()

        feature_collection = {
            "type": "FeatureCollection",
            "features": [
                geojson
            ]
        }

        return feature_collection

def add_vector_layer_to_map(geojson, dataset_title):
    if 'errors' in geojson:
        st.error('Layer could not be fetched', icon="🚨")        
    else:
        map = create_map()
        folium.GeoJson(geojson, name=dataset_title).add_to(map)
        st.session_state.map = map


def add_raster_layer_to_map(gdf):
    choropleth = folium.Choropleth(
        geo_data=gdf,
        name='choropleth',
        data=gdf,
        # columns=['name', column_name],
        key_on='feature.properties.name',
        fill_color='YlGn',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Legend Name',
        highlight=True,
        line_color='black',
        line_weight=1,
        # tooltip=folium.features.GeoJsonTooltip(fields=['name', 'ID', column_name], labels=True, sticky=True)
    ).add_to(st.session_state.map)
    # folium.GeoJson(gdf, name='geojson', tooltip=folium.features.GeoJsonTooltip(fields=['name', column_name])).add_to(m)

if 'ckan' not in st.session_state:
    st.session_state.ckan = RemoteCKAN('https://wifire-data.sdsc.edu/', apikey=os.environ['apiKey'])

with st.sidebar:
    st.write('information about data')
    search = st.text_input('Search WIFIRE Data Catalog')

    if (len(search) > 0 and 'search' not in st.session_state) \
            or ('search' in st.session_state and st.session_state.search != search):
        st.session_state.search = search

        response = st.session_state.ckan.action.package_search(q=st.session_state.search + '+res_format=GeoJSON', start=0, rows=50)
        datasets = response["results"]

        st.session_state.search_results = datasets

    if 'search_results' in st.session_state:
        with st.expander("Search Results: ", expanded=True):
            result_list = {}
            for result in st.session_state.search_results:
                col1, col2 = st.columns([2,1])
                with col1:
                    result_list[result['id']] = st.checkbox(result['title'], key=result['id'])
                with col2:
                    st.link_button("View Metadata", url='https://wifire-data.sdsc.edu/dataset/' + result['id'])
                                        
            st.session_state.result_list = result_list
 

    if 'result_list' in st.session_state:

        # check to see if prev selected ids is same
        checked_ids = [list(st.session_state.result_list.keys())[idx] \
                for idx, value in enumerate(st.session_state.result_list.values()) \
                if value]
    
        prev_selected_ids = [x['id'] for x in st.session_state.selected_datasets] if 'selected_datasets' in st.session_state else []

        # if there is a new checked id or different lengths  
        if len([x for x in checked_ids if x not in prev_selected_ids]) > 0 or len(checked_ids) != len(prev_selected_ids):  
            st.session_state.selected_datasets = [x for x in st.session_state.search_results if x['id'] in checked_ids]   

            ## parse selected datasets for file info            
            
            for data in st.session_state.selected_datasets[:3]:
                if data['owner_org'] == 'e2d487d1-6973-487c-bb20-a11744d9e1ea': #OpenTopography
                    geojson = get_opentopo_geojson(data['url'])
                    add_vector_layer_to_map(geojson, data['title'])
                for resource in data['resources']:
                    if resource['format'] == 'GeoJSON':
                        geojson = get_geojson(resource)
                        add_vector_layer_to_map(geojson, data['title'])
                        break # only add one layer
                    elif resource['format'] == 'GeoTIFF' or resource['format'] == 'TIFF':
                        add_raster_layer_to_map(resource)
                        break # only add one layer


st.title('WIRED Map Interface')


if 'map' in st.session_state:
    # if 'errors' in st.session_state:
    #     st.error(st.session_state.errors) 

    folium_static(st.session_state.map)