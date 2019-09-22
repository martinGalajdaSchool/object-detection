#!/usr/bin/env bash

cd /storage/brno3-cerit/home/marneyko/object-detection

module unload cuda-8.0
module unload tensorflow-1.7.1-gpu-python3
module unload python-3.4.1-gcc
module unload python34-modules-gcc

module load python36-modules-gcc
module load python-3.6.2-gcc

source ./venv/bin/activate

module load cuda-9.0

echo "Echoing cuda visible devices"
echo $CUDA_VISIBLE_DEVICES
echo "Donee echoing cuda visible devices"

export LD_LIBRARY_PATH=./tmp-cudnn/usr/lib/x86_64-linux-gnu/:$LD_LIBRARY_PATH

cd /storage/brno3-cerit/home/marneyko/object-detection &&
    module load cuda-9.0 python36-modules-gcc python-3.6.2-gcc &&
    source ./venv/bin/activate &&
    export LD_LIBRARY_PATH=./tmp-cudnn/usr/lib/x86_64-linux-gnu/:$LD_LIBRARY_PATH &&
    python retrain.py \
        --model=inceptionV3 \
        --images_num=3000000 \
        --batch_size=32 \
        --workers=4 \
        --optimizer=adam \
        --unfreeze_top_k_layers=0 \
        --continue_from_last_checkpoint=f \
        --use_multitarget_learning=t \
        --continue_training_allowed_different_config_keys=continue_training_allowed_different_config_keys,workers,epochs,db_images_path,db_image_labels_path,continue_from_last_checkpoint,optimizer_lr
