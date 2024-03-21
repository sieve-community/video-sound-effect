import sieve
import tempfile

metadata = sieve.Metadata(
    title="Generate AI Sound Effects",
    description="Generate sound effects for stock videos using AI.",
    code_url="https://github.com/sieve-community/video-sound-effect",
    image=sieve.Image(
        path="sound-effect-icon.webp"
    ),
    tags=["Video", "Sound", "Showcase"],
    readme=open("README.md", "r").read(),
)

@sieve.function(
    name="video-sound-effect",
    system_packages=["libgl1-mesa-glx", "libglib2.0-0", "ffmpeg"],
    metadata=metadata
)
def video_sound_effect(video: sieve.File, duration: float = 5.0) -> sieve.File:
    '''
    :param video: The video to generate a sound effect for.
    :param duration: The duration of the sound effect in seconds. Must be less than 20 seconds.
    '''
    if duration > 20.0:
        raise ValueError("Duration must be less than 20 seconds")
    if duration < 0.0:
        raise ValueError("Duration must be greater than 0 seconds")
    
    print("getting video length...")
    import subprocess
    command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{video.path}'"
    video_length = float(subprocess.check_output(command, shell=True).decode('utf-8').strip())

    if video_length < duration:
        raise ValueError("Video length must be greater than duration")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print("cutting video to match duration...")
        output_video_path = f'{temp_dir}/cut_video.mp4'
        command = f'ffmpeg -y -i "{video.path}" -t {duration} -c copy "{output_video_path}"'
        result = subprocess.run(command, shell=True, stderr=subprocess.PIPE)
        
        print("getting middle frame of video...")
        middle_time = duration / 2
        middle_frame_path = f'{temp_dir}/frame.png'
        command = f"ffmpeg -y -i '{output_video_path}' -ss {middle_time} -vframes 1 '{middle_frame_path}'"
        result = subprocess.run(command, shell=True, stderr=subprocess.PIPE)

        print("asking model to describe the video...")
        cogvlm = sieve.function.get("sieve/cogvlm-chat")
        prompt = "describe what you might hear in this video in detail."
        description = cogvlm.run(sieve.Image(path=middle_frame_path), prompt)

        print("generating sound effect...")
        audiogen = sieve.function.get("sieve/audioldm")
        sound = audiogen.run(description, duration)
        sound_path = sound.path

        # if there was sound in the video, remove it
        print("checking if video has sound...")
        command = f'ffprobe -v error -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 "{output_video_path}"'
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        if b'audio' in result.stdout:
            print("removing sound from video...")
            mute_video_path = f'{temp_dir}/mute.mp4'
            command = f'ffmpeg -y -i "{output_video_path}" -c copy -an "{mute_video_path}"'
            subprocess.call(command, shell=True, stderr=subprocess.PIPE)
            output_video_path = mute_video_path
        
        final_video_path = f'final_video.mp4'
        # Add sound to video
        print("adding sound to video...")
        command = f'ffmpeg -y -i "{output_video_path}" -i "{sound_path}" -c:v copy -c:a aac -strict experimental "{final_video_path}"'
        subprocess.call(command, shell=True, stderr=subprocess.PIPE)

        return sieve.File(path=final_video_path)

if __name__ == "__main__":
    video = sieve.File(path="bee.mp4")
    duration = 5.0
    print(video_sound_effect(video, duration))