import ffmpeg
(
    ffmpeg.input("D:\OBS\\20240305_165623_old.mxf").output("D:\OBS\\20240305_165623.mxf",c='copy',timecode="01:00:00:00").run()
)