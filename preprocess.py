# import moviepy
import numpy as np
from moviepy.video.fx.all import crop
from moviepy.editor import *
from math import floor
from PIL import Image
from pytesseract import image_to_string
from itertools import groupby

# overlay windows:
# <----------------------> width_name
# <-----------------------------------> width_overlay
# | G. Thomas ----------- | FLAG | SKY | TIME
#                                 <---> width_team = 80
#                                     <-> white_pad
# topleft corner is at (x1_overlay, y1_overlay)
# time is overlain in white otherwise could be different label

# parameters
x1_overlay = 169
y1_overlay = 890
width_overlay = 586
height_overlay = 45
width_name = 400
width_team = 110

width_flag = 70
width_team = 115
width_white_pad = 10

maxdev = 5
windowsize = 5
refcolor = np.array([246, 170, 41], dtype=np.uint8)
whiterefcolor = np.array([255, 250, 252], dtype=np.uint8)
fps = 1

DEBUG_FLAG = 0

print('loading video and prepare for analysis')
# load frame
clip = VideoFileClip("tdf2018-20.mp4").without_audio().set_fps(fps)

# save frame for reference pixel finding
if DEBUG_FLAG:
    clip.save_frame("frame_riding.png", t='03:06:30')
    clip.save_frame("frame_finish.png", t='03:07:00')

substart = '00:00:00'
subend   = '00:30:00'
#%%
subclip = clip.subclip(substart, subend)
# crop subframes
overlay_clip = crop(subclip,
                    x1=x1_overlay,
                    y1=y1_overlay,
                    x2=x1_overlay + width_overlay,
                    y2=y1_overlay + height_overlay)

# crop in subframes
name_clip = crop(overlay_clip, x2=width_name)
team_clip = crop(overlay_clip, x1=width_overlay-width_team, x2=width_overlay)
colorpixel_clip = crop(overlay_clip, x2=width_name)
pixelcolor = crop(name_clip,
                  x1=width_name - 2*windowsize,
                  y1=round(height_overlay / 2) - round(windowsize/2),
                  x2=width_name - windowsize,
                  y2=round(height_overlay / 2) + round(windowsize/2))
whitecolor = crop(subclip,
                  x1=x1_overlay+ width_overlay + width_white_pad,
                  y1=y1_overlay+round(height_overlay / 2) - round(windowsize/2),
                  x2=x1_overlay+ width_overlay + width_white_pad + windowsize,
                  y2=y1_overlay+round(height_overlay / 2) + round(windowsize/2))


#name_clip.write_videofile("name.mp4")
#team_clip.write_videofile("team.mp4")
#pixelcolor.write_videofile("pixelcolor.mp4")
#whitecolor.write_videofile("whitecolor.mp4")

#%%
print('performing color analysis')
# loops over each color channel and returns true if all channels are within range
def color_in_range(pixels, refcolor):
    color = np.round(np.average(np.reshape(pixels, [-1, 3]), axis=0))
    for (c, r) in zip(color, refcolor):
        rgbrange = range(r - maxdev, r + maxdev)
        if c not in rgbrange:
            return False
    return True

# apply function on the iterator
colormatches = [color_in_range(c, refcolor) for c in pixelcolor.iter_frames()]
whitematches = [color_in_range(c, whiterefcolor) for c in whitecolor.iter_frames()]
# union
isRiderLabelFrame = [c & w for (c,w) in zip(colormatches, whitematches)]

#%% zip same array with lag of one to detect changes, then write the new value
# as well as the index into the new list, also prepend the first element
print('calculating color changes')
def colorchange(lst):
    out = [(0, lst[0])]
    lst_short = lst[:-1]
    lst_lag_plus_one = lst[1:]
    for (previdx, (prevval, val)) in enumerate(zip(lst_short, lst_lag_plus_one)):
        if prevval != val:
            out += [(previdx+1, val)]
    return out

# is an array of (index, value) where a change of color occured
riderLabelTransition = colorchange(isRiderLabelFrame)

#%% takes the changes, and filters all that are shorter than one second
# also calculates the duration of each change to the next (including last to end)
# output an array of (index, value, duration), duration in frames of filtered changes
# possibly two same values can occur after filtering
# also sum of duration might not match actual duration since the
# duration of the spikes is removed
print('removing spikes in data')
def filterspikes(lst):
    out = []
    lst_short = lst[:-1]
    lst_lag_plus_one = lst[1:]
    for ((i1, v1), (i2, v2)) in zip(lst_short, lst_lag_plus_one):
        duration = (i2-i1) / subclip.fps
        if duration >= 1:
            out += [(i1, v1, i2-i1)]

    # now add last frame (that runs until the stream ends)
    last_idx, last_val = lst[-1]
    out += [(last_idx, last_val, floor(subclip.end*subclip.fps)-last_idx)]
    return out

filteredTransitions = filterspikes(riderLabelTransition)
if DEBUG_FLAG:
    print(filteredTransitions)

#%% merge duplicates in a row

# filter all non unique elements but instead
# of removing them calculate new duration as
# duration_unique = start_duplicate + duration_duplicate - start_unique
# where duplicate is only the last of the duplicates in a row
print('merging identical subsequent values')
def mergefiltered(filteredchanges):
    (_, prevkey, _) = filteredchanges[0]
    out = []
    queue = []

    # assumes non-empty queue
    def flushqueue(queue):
        (fi, vq, _) = queue[0]
        (fl, _, dq) = queue[-1]
        return ([], [(fi, vq, fl + dq - fi)])

    for (i, v, d) in filteredchanges:
        if prevkey != v:
            prevkey = v;
            # flush queue
            print("flush:")
            print(queue)
            if len(queue) > 0:
                (queue, newel) = flushqueue(queue)
                out += newel
        queue += [(i,v,d)]

    # now flush queue a last time
    (_, lastel) = flushqueue(queue)
    return out + lastel

mergedTransitions = mergefiltered(filteredTransitions)

#%% get desired output
# - only take true values
# - get start and end time in index (for ocr) and seconds (stats)
# output should be a list of
# (start_idx, end_idx, start_time, end_time)

riderLabel = [(i,i+d,i/fps, (i+d)/fps) for (i,v,d) in mergedTransitions
              if v == True]

print("riders:")
print(riderLabel)
#%% ocr
print('performing ocr')
name = []
team = []
def performOCR(subclip, frameid):
    imarr = subclip.get_frame(frameid)
    im = Image.fromarray(imarr)
    return image_to_string(im)

# perform ocr for center shot of every element
for (istart,iend,tstart,tend) in riderLabel:
    centerframeid = round((istart + iend)/2)
    name += [performOCR(name_clip, centerframeid)]
    team += [performOCR(team_clip, centerframeid)]

print(name)
print(team)



#%% now zip everything
import pandas as pd
print('putting it together and store to hdf')
riderCoverageRaw = [(tstart, tend, name, team) for ((_,_,tstart, tend), name, team) in zip(riderLabel, name, team)]
print(riderCoverageRaw)
df = pd.DataFrame(riderCoverageRaw)

# and save
store = pd.HDFStore('tdf_coverage_raw.h5')
store[substart + '-' + subend] = df

store.close()