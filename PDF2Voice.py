import os
import torch
from openvoice import se_extractor
from openvoice.api import ToneColorConverter
from random import randint
import argparse
import json
import fitz
from pydub import AudioSegment
import re


def setup_args():
    parser = argparse.ArgumentParser(description='PDF2Voice')
    # read the json config.
    with open('config.json') as f:
        config:dict = json.load(f)
    if not config:
        raise ValueError("Config file is empty. Go copy it from the repo.")
    
    type_map = {
        "int": int,
        "float": float,
        "str": str,
        "bool": bool
    }

    for key, arg in config.items():
        help = arg["help"] if "help" in arg else None
        default = arg["value"] if "value" in arg else None
        nargs = arg["nargs"] if "nargs" in arg else None
        parser.add_argument(f"--{key}",
                            type=type_map[arg["type"]],
                            default=default,
                            help=help,
                            nargs=nargs,
                            required= not "value" in arg
                            )
    return parser

def pdf_to_text(pdf_path:str, pages:str = "all"):
    with fitz.open(pdf_path) as pdf:
        text = ""

        # determine the pages to extract
        if pages == "all":
            p1 = p2 = None
            pages = range(len(pdf))
        elif "," in pages:
            pages = [int(p.strip())-1 for p in pages.split(",")]
        elif "-" in pages:
            if pages.count("-") > 1:
                raise ValueError("Invalid page range format. Use either 1,2,3 or 1-3")
            p1, p2 = pages.split("-")
            p1 = int(p1) - 1
            p2 = int(p2)
            pages = range(p1, p2)
        else:
            try:
                p1 = int(pages) - 1
                p2 = int(pages)
            except ValueError:
                raise ValueError("Invalid page range format. Use either 1,2,3 or 1-3")
            if type(pages) is list:
                pass
            else:
                pages = range(p1, p2)

        for i in pages:
            page = pdf[i]
            text += page.get_text()
    return text

def merge_wavs(wav_files, output_file):
    # Load the first file
    combined = AudioSegment.from_wav(wav_files[0])
    
    # Append the rest of the wav files
    for wav in wav_files[1:]:
        audio = AudioSegment.from_wav(wav)
        combined += audio
    
    # Export the merged wav file
    combined.export(output_file, format="wav")

if __name__ == '__main__':
    parser = setup_args()
    args = parser.parse_args()

    voice = args.voice
    voice_speed = args.voice_speed
    voice_directory = args.voice_directory
    OV_SPEAKER = args.OV_SPEAKER
    OV_MODEL = args.OV_MODEL
    output = args.output
    device = args.device
    input_path = args.input
    ckpt_path = args.ckpt_path
    pages = args.pages
    keep_intermediate = args.keep_intermediate
    chunk_size = args.chunk_size
    Melo_Language = args.Melo_Language

    # check the input file
    input_is_pdf = input_path.endswith(".pdf")
    if (not input_path.endswith(".pdf")) and (not input_path.endswith(".txt")):
        raise ValueError("Input file must be a pdf file.")
    elif not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file {input_path} not found.")
    input_name = os.path.basename(input_path).split(".")[0]

    # getting the text from the pdf or txt file
    input_texts = []
    if input_is_pdf:
        tmp_txt = pdf_to_text(input_path, pages.strip())
    else:
        with open(input_path, 'r') as f:
            tmp_txt= f.read().split(" ")
    
    tmp_txt = tmp_txt.replace("\n", " ")

    # remove anything within square brackets using regex
    tmp_txt = re.sub(r'\[\d*\]–\[\d*\]|\[\d*\]', '', tmp_txt)
    tmp_txt = re.sub(r'-\s|-\s', '', tmp_txt)

    # split for every X words
    tmp_txt = tmp_txt.split(" ")
    chunk = ""
    end_chunk = False
    for i in range(0, len(tmp_txt)):
        word = tmp_txt[i]

        # we replace fully capitalized words with the the seperated characters
        if word.isupper():
            word = " ".join([c.upper() for c in word])

        chunk += word + " "
        if i % chunk_size == 0 and i != 0:
            end_chunk = True
        
        if (end_chunk and word.endswith(".")) or i == len(tmp_txt)-1:
            input_texts.append(chunk)
            chunk = ""
            end_chunk = False

    # see if the output is a directory
    output_is_dir = os.path.basename(output).split(".").__len__() == 1

    # make the output directory if it doesn't exist
    if output_is_dir:
        os.makedirs(output, exist_ok=True)

    # initailize the model
    if device == "auto":
        device="cuda" if torch.cuda.is_available() else "cpu"
    tone_color_converter = ToneColorConverter(os.path.join(ckpt_path,'converter', 'config.json'), device=device)
    tone_color_converter.load_ckpt(os.path.join(ckpt_path,'converter', 'checkpoint.pth'))

    # obtain the tone color of the input audio
    target_se, audio_name = se_extractor.get_se(os.path.join(voice_directory,voice+".mp3"), tone_color_converter, vad=False)

    from melo.api import TTS
    source_se = torch.load(os.path.join(ckpt_path, 'base_speakers', 'ses', f'{OV_MODEL}.pth'), map_location=device)
    model = TTS(Melo_Language, device=device)
    speaker_ids = model.hps.data.spk2id
    print(f"Speaker IDs: {speaker_ids.keys()}")
    speaker_id = speaker_ids[OV_SPEAKER]

    processed_audio_paths = []
    temp_audio_paths = []
    for count, text_chunk in enumerate(input_texts):
        # generating intermediate
        if output_is_dir:
            temp_file_path = os.path.join(output, input_name+f".temp({count}).wav")
            real_output = os.path.join(output, f"{input_name}({count}).wav")
        else:
            temp_file_path = os.path.join(*output.split(os.path.sep)[:-1], os.path.basename(output).split(".")[0]+f".temp({count}).wav")
            real_output = output.split(".")[0]+f"({count}).wav"
        processed_audio_paths.append(real_output)
        model.tts_to_file(text_chunk, speaker_id, temp_file_path, speed=voice_speed)
        print(f"Generated intermediate audio file: {temp_file_path}")
        temp_audio_paths.append(temp_file_path)

        # converting to the target voice
        print(f"Converting to the target voice... {count} of {len(input_texts)-1}")
        encode_msg = "@ogelbw"
        tone_color_converter.convert(
                    audio_src_path=temp_file_path,
                    src_se=source_se,
                    tgt_se=target_se,
                    output_path=real_output,
                    message=encode_msg)
    
    # merge the audio files
    final_output = output if not output_is_dir else os.path.join(output, f"{input_name}.wav")
    merge_wavs(processed_audio_paths, final_output)

    # remove the temporary files
    if not keep_intermediate:
        for f in processed_audio_paths:
            os.remove(f)
        for f in temp_audio_paths:
            os.remove(f)

    print(f"Final output generated at: {final_output}")


