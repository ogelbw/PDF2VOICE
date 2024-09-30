## WHY??
After a specially exciting day of ONLY reading technical white papers and uni course notes I came to the realisation that 1: I find white papers boring and 2: I get tired (and distracted) while reading.\
This repo is the natural extension of that train of thought.

## installation
The tts module `doesn't` work on newer version of python, This project has been tested on `python 3.9`.

First clone this project:
```bash
git clone https://github.com/ogelbw/PDF2VOICE.git
```

>I recommend using a virtual environment for this project, you can create one with the following:
>```bash
>python3.9 -m venv ./venv
>```
>And then activate it:
>```bash
>source ./venv/bin/activate
>```
>Or if you're on windows:
>```bash
>./venv/bin/activate
>```


This project also relies on MelloTTS, you can install this with the following:
```bash
git clone https://github.com/myshell-ai/MeloTTS.git
cd MeloTTS
pip install -e .
python -m unidic download
```

This project relies on OpenVoice, you can install this with the following (or you could do this the supported way and install it with docker see: https://github.com/myshell-ai/OpenVoice/tree/main):
```bash
git clone https://github.com/myshell-ai/OpenVoice.git
cd OpenVoice
pip install -e .
```

Then you can install the rest of the dependencies with:
```bash 
pip install -r requirements.txt
```

Now you need to download the checkpoint used for generating the intermediate voice:
download the models from myshell [here](https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip).

Then extract the contents of the zip file into the root of this project.

You also need to go and install `ffmpeg`.

## note to linux users
Despite pip installing torch and the needed packages for cuda the tts module will not be able to find the .so files related needed. These do exist in the python sitepackages under `venv/lib/python3.9/site-packages/nvidia/<cuda or cublas>` copy the `.so` files from there to the root of the project. (yes this is jank.) 

## setup
Now that you have everything installed you need to go out and find a small voice clip that you want to use for the tts to clone. Go find one on youtube or something and place it in the `./voices` directory or use the one of neuro I was testing with. The voices need to be in the `.wav` format.

You should look at the `config.json` file and make changes as you see appropriate. Each field can be overridden by the command line arguments of the same name. e.g. `--voice` will override the `voice` field in the config file.

## Typical usage

```bash
source ./venv/bin/activate

python main.py --input "path/to/input.pdf" --pages "2-6"
```
