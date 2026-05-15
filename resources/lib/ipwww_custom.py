# -*- coding: utf-8 -*-

import sys
import os
import re
from datetime import datetime

import requests
from requests.packages import urllib3
#Below is required to get around an ssl issue
urllib3.disable_warnings()
import urllib
import html
import codecs
import time

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

try:
    import cookielib
except:
    import http.cookiejar
    cookielib = http.cookiejar

         
def log_message(message, level=xbmc.LOGINFO):
    """
    Logs a message to the Kodi log file.
    
    :param message: The text to log
    :param level: Kodi log level (default: LOGINFO)
    """
    try:
        if not isinstance(message, str):
            message = str(message)
        xbmc.log(f"[BBC iPlayer] {message}", level)
    except Exception as e:
        xbmc.log(f"[BBC iPlayer] Logging failed: {e}", xbmc.LOGERROR)


def strip_before(text: str, marker: str) -> str:
    """Remove all characters before the first occurrence of marker."""
    if not marker:
        raise ValueError("Marker string cannot be empty.")
    
    index = text.find(marker)
    if index == -1:
        return text  # Marker not found, return original string
    return text[index:]
 
 
def strip_after(text: str, marker: str) -> str:
    """
    Removes everything after the first occurrence of `marker` in `text`.
    If marker is not found, returns the original text.
    """
    if not isinstance(text, str) or not isinstance(marker, str):
        raise TypeError("Both text and marker must be strings.")
    if marker == "":
        raise ValueError("Marker cannot be an empty string.")

    index = text.find(marker)
    if index != -1:
        return text[:index]  # Keep everything before marker
    return text  # Marker not found, return original       


def create_af3_style_episode_header(subtitle, title, debug, itemtype):
    """
    Creates an AF3 style "Episode Header" from different iPlayer episode "subtitle" formats
    
    Ref.        Input subtitle Format     Input Title Format                   Output Format           Watching    Recommendations
    ----        ---------------------     ------------------                   -------------           --------    ---------------
    Format 1    Series N: NN. EpisodeTitle                                     NxNN. EpisodeTitle          Yes             Yes
    Format 2    Series N: London                                               Nx00. EpisodeTitle          Yes
    Format 3    Series N: Episode N                                            NxNN. Episode N                             Yes
    Format 4    Episode N                                                      1xNN. Episode N             Yes
    Format 5    N. EpisodeTitle                                                1xNN. EpisodeTitle                          Yes
    Format 6    None                      ShowTitle                            1x01. ShowTitle                             Yes
    Format 7    MovieTitle or tagline     MovieTitle                           MovieTitle or tagline       Yes             Yes
    """
    
    color_white = "[COLOR white]"
    color_end = "[/COLOR]"
    
    # process Format 7
    if itemtype == 'movie':
         af3_episode_header = "[B]" + subtitle + "[/B][CR]" 
         af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
         return af3_episode_header_colour    
    
    # process Format 6
    if subtitle == 'None':
        if debug == True:
            log_message('AF3 HEADER PROCESSING FORMAT 6 FOR SUBTITLE = ' + subtitle)
        af3_episode_header = "[B]" + '1x01. ' + title + "[/B][CR]" 
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        return af3_episode_header_colour
   
    # process Format 4
    if subtitle.startswith("Episode"):
        if debug == True:
            log_message('AF3 HEADER PROCESSING FORMAT 4 (STARTS WITH EPISODE) FOR SUBTITLE = ' + subtitle)
        series_nr = "1"
        episode_1 = subtitle.replace('Episode ','')
        if len(episode_1) == 1:
            episode_nr = '0' + episode_1
        else:
            episode_nr = episode_1
        af3_episode_header = "[B]" + series_nr + 'x' + episode_nr + '. ' + 'Episode ' + episode_1 + "[/B][CR]"
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        return af3_episode_header_colour
        
    # process Format 5
    if "Series" not in subtitle and subtitle != 'None':
        if debug == True:
            log_message('AF3 HEADER PROCESSING FORMAT 5 FOR (DOES NOT CONTAIN SERIES) FOR SUBTITLE = ' + subtitle)
        series_nr = '1'
        index = subtitle.find('.')
        episode_1 = subtitle[:index]        
        if index == 1:
            episode_nr = '0' + episode_1
        else:
            episode_nr = episode_1
        episode_title = subtitle[index + 2:]
        af3_episode_header = "[B]" + series_nr + "x" + episode_nr + ". " + episode_title + "[/B][CR]"
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        return af3_episode_header_colour
    
    # debug message for Formats 1 2 and 3
    if debug == True:
        log_message('AF3 HEADER PROCESSING for FORMATS 1 2 AND 3 FOR SUBTITLE = ' + subtitle)
        
    # reformat subtitle if input is Format 3
    index = subtitle.find('Episode') # returns -1 if not found
    if index > 1:
        if debug == True:
            log_message('AF3 HEADER PROCESSING FORMAT 3 FOR SUBTITLE = ' + subtitle)
        d0 = strip_before(subtitle,'Episode')
        d1 = subtitle.replace('Episode ','')
        d2 = d1 + '.'
        subtitle = d2 + ' ' + d0
    
    # get series number
    t1 = subtitle[7:] # remove "Series " from start of description
    series_nr = strip_after(t1,":")
    
    # get episode number
    t2 = t1.find(" ")
    t3 = t1[t2+1:]
    t4 = strip_after(t3,".")
    try: # obtain episode number if possible, otherwise set to 0
        episode_nr = int(t4)
        if debug == True:
            log_message('AF3 HEADER PROCESSING FORMAT 1/3 FOR SUBTITLE = ' + subtitle)
    except Exception: # Format 2
        episode_nr = 0
        if debug == True:
            log_message('AF3 HEADER PROCESSING FORMAT 2 FOR SUBTITLE = ' + subtitle)
    episode_nr_pad = f"{episode_nr:02d}"
    episode_nr_pad_str = str(episode_nr_pad)
    
    # get episode title
    t5 = strip_before(t1,".")
    episode_title = t5[2:]
    
    # create AF3 style episode header
    af3_episode_header = "[B]" + str(series_nr) + "x" + episode_nr_pad_str + ". " + episode_title + "[/B][CR]" 
    af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
    if debug == True:
        log_message('AF3 HEADER PROCESSING OUTPUT = '+ af3_episode_header_colour)

    return af3_episode_header_colour     