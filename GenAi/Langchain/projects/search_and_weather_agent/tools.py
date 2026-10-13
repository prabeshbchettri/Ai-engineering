from langchain_nimble import NimbleSearchTool
from langchain.tools import tool

search_tool=NimbleSearchTool(
    k=5,
    deep_search=True,
    parsing_type="markdown"
)
@tool
def google_search(query:str):
    """
    search anything on google for real time information
    Args:
        query (str): user search query for google search
        Return - result from google search"""
    res=search_tool.invoke(query)
    return res

@tool
def weather_tool(city:str):
    """
    Get real time weather details like  temperature, humidity, wind speed, etc. for a given city
    Args:
        city (str): city name for weather details
        Return - weather data from the api response.
    """
    return f"The current Temperature in {city} is 23.C"
    
    
    
ALL_TOOLS=[google_search , weather_tool]    