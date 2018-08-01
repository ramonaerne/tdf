# import moviepy
import numpy as np
from moviepy.video.fx.all import crop
from moviepy.editor import *
from math import floor
from PIL import Image
from pytesseract import image_to_string
from itertools import groupby

# parameters
x1_overlay = 112
y1_overlay = 593
width_overlay = 393
height_overlay = 29
width_name = 265
width_team = 80
# overlay windows:
# <----------------------> width_name = 265
# <-----------------------------------> width_overlay = 393
# | G. Thomas ----------- | FLAG | SKY | ... (time etc)
#                                 <---> width_team = 80
# topleft corner is at (x1_overlay, y1_overlay)

maxdev = 6
windowsize = 5
refcolor = np.array([250, 172, 42], dtype=np.uint8)

fps = 1

# load frame
clip = VideoFileClip("s20_youtube.mp4").without_audio().set_fps(fps)

# crop subframesnnn
overlay_clip = crop(clip,
                    x1=x1_overlay,
                    y1=y1_overlay,
                    x2=x1_overlay + width_overlay,
                    y2=y1_overlay + height_overlay)

name_clip = crop(overlay_clip, x2=width_name)
team_clip = crop(overlay_clip, x1=width_overlay-width_team, x2=width_overlay)

# testsvave
#name_clip.write_videofile("test_name.mp4")
#team_clip.write_videofile("test_team.mp4")
#%%

# get cornerframe for color detection
# maximum allowed color deviation on each channel
# this is introduced due to videocompression
# also average over multiple pixel for more robustness
# crop a small window in the end of the name crop
# (where no name should be hopefully)
# of windowsize to detect color, then iterate over all frames
pixelcolor = crop(name_clip,
                  x1=width_name - 2*windowsize,
                  y1=round(height_overlay / 2) - round(windowsize/2),
                  x2=width_name - windowsize,
                  y2=round(height_overlay / 2) + round(windowsize/2))

pixelcolor.write_videofile("test_pixel.mp4")

#%%
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


# takes the changes, and filters all that are shorter than one second
# also calculates the duration of each change to the next (including last to end)
# output an array of (index, value, duration), duration in frames of filtered changes
# possibly two same values can occur after filtering
# also sum of duration might not match actual duration since the
# duration of the spikes is removed
def filterspikes(lst):
    out = []
    lst_short = lst[:-1]
    lst_lag_plus_one = lst[1:]
    for ((i1, v1), (i2, v2)) in zip(lst_short, lst_lag_plus_one):
        duration = (i2-i1) / clip.fps
        if duration >= 1:
            out += [(i1, v1, i2-i1)]

    # now add last frame (that runs until the stream ends)
    last_idx, last_val = lst[-1]
    out += [(last_idx, last_val, floor(clip.end*clip.fps)-last_idx)]
    return out

filteredchanges = filterspikes(changes)
print(filteredchanges)

#%% merge duplicates in a row

# filter all non unique elements but instead
# of removing them calculate new duration as
# duration_unique = start_duplicate + duration_duplicate - start_unique
# where duplicate is only the last of the duplicates in a row
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

mergedchanges = mergefiltered(filteredchanges)
print("merged")
print(mergedchanges)

#%% get desired output
# - only take true values
# - get start and end time in index (for ocr) and seconds (stats)
# output should be a list of
# (start_idx, end_idx, start_time, end_time)

riderlabel = [(i,i+d,i/fps, (i+d)/fps) for (i,v,d) in mergedchanges
              if v == True]

name = []
team = []
def performOCR(clip, frameid):
    imarr = clip.get_frame(frameid)
    im = Image.fromarray(imarr)
    return image_to_string(im)

# perform ocr for center shot of every element
for (istart,iend,tstart,tend) in riderlabel:
    centerframeid = round((istart + iend)/2)
    name += [performOCR(name_clip, centerframeid)]
    team += [performOCR(team_clip, centerframeid)]

print(name)
print(team)

# takes the changes, and filters all that are shorter than one second
# also calculates the duration of each change to the next (including last to end)
# output an array of (index, value, duration), duration in frames of filtered changes
# possibly two same values can occur after filtering
# also sum of duration might not match actual duration since the
# duration of the spikes is removed
def filterspikes(lst):
    out = []
    lst_short = lst[:-1]
    lst_lag_plus_one = lst[1:]
    for ((i1, v1), (i2, v2)) in zip(lst_short, lst_lag_plus_one):
        duration = (i2-i1) / clip.fps
        if duration >= 1:
            out += [(i1, v1, i2-i1)]

    # now add last frame (that runs until the stream ends)
    last_idx, last_val = lst[-1]
    out += [(last_idx, last_val, floor(clip.end*clip.fps)-last_idx)]
    return out

filteredchanges = filterspikes(changes)
print(filteredchanges)

#%% merge duplicates in a row

# filter all non unique elements but instead
# of removing them calculate new duration as
# duration_unique = start_duplicate + duration_duplicate - start_unique
# where duplicate is only the last of the duplicates in a row
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

mergedchanges = mergefiltered(filteredchanges)
print("merged")
print(mergedchanges)

#%% get desired output
# - only take true values
# - get start and end time in index (for ocr) and seconds (stats)
# output should be a list of
# (start_idx, end_idx, start_time, end_time)

riderlabel = [(i,i+d,i/fps, (i+d)/fps) for (i,v,d) in mergedchanges
              if v == True]

name = []
team = []
def performOCR(clip, frameid):
    imarr = clip.get_frame(frameid)
    im = Image.fromarray(imarr)
    return image_to_string(im)

# perform ocr for center shot of every element
for (istart,iend,tstart,tend) in riderlabel:
    centerframeid = round((istart + iend)/2)
    name += [performOCR(name_clip, centerframeid)]
    team += [performOCR(team_clip, centerframeid)]

print(name)
print(team)
#%% try to get a text overlay
def txt_choice(m, tstart, duration):
    if m:
        return TextClip("T", fontsize=20, color='black')\
                        .set_position('center')\
                        .set_duration(duration)\
                        .set_start(tstart)
    else:
        return TextClip("F", fontsize=20, color='black')\
            .set_position('center')\
            .set_duration(duration)\
            .set_start(tstart)


#%%

txt_overlay = [txt_choice(val, t/clip.fps, d/clip.fps) for (t, val, d) in filteredchanges]

# save frame
overlay_clip.save_frame("frame_text.png", t='00:00:01')
#clip.save_frame("frame_2.png", t='00:00:20')
# save overlay clip
overlaycrop = CompositeVideoClip([overlay_clip] + txt_overlay)
overlaycrop.write_videofile("test_overlay.mp4")

#%% Next: Add OCR to clip

