# pyaudio install em Mac M2
$ brew uninstall portaudio
$ pip3 uninstall pyaudio
$ arch -arm64 /opt/homebrew/bin/brew install portaudio
$ pip3 install --no-cache-dir --global-option='build_ext' --global-option='-I/opt/homebrew/Cellar/portaudio/19.7.0/include' --global-option='-L/opt/homebrew/Cellar/portaudio/19.7.0/lib' pyaudio
$ pip install ffmpeg-python