################################################################################
# Copyright (c) 2021 ContinualAI.                                              #
# Copyrights licensed under the MIT License.                                   #
# See the accompanying LICENSE file for terms.                                 #
#                                                                              #
# Date: 10-10-2020                                                             #
# Author: Vincenzo Lomonaco                                                    #
# E-mail: contact@continualai.org                                              #
# Website: www.continualai.org                                                 #
################################################################################

""" INATURALIST2018 Pytorch Dataset
Info: https://www.kaggle.com/c/inaturalist-2018/data
Download: https://github.com/visipedia/inat_comp/tree/master/2018
Based on survey in CL: https://ieeexplore.ieee.org/document/9349197

Images have a max dimension of 800px and have been converted to JPEG format

You can select supercategories to include. By default 10 Super categories are
selected from the 14 available, based on at least having 100 categories (leaving
out Chromista, Protozoa, Bacteria), and omitting a random super category from
the remainder (Actinopterygii).

Example filename from the JSON:
 "file_name": "train_val2018/Insecta/1455/994fa5...f1e360d34aae943.jpg"
"""

import os
import logging
from torch.utils.data.dataset import Dataset
from torchvision.transforms import ToTensor
from PIL import Image
from os.path import expanduser
import json
import pprint

from .inaturalist_data import INATURALIST_DATA


def pil_loader(path):
    """ Load an Image with PIL """
    # open path as file to avoid ResourceWarning
    # (https://github.com/python-pillow/Pillow/issues/835)
    with open(path, 'rb') as f:
        img = Image.open(f)
        return img.convert('RGB')


def _isArrayLike(obj):
    return hasattr(obj, '__iter__') and hasattr(obj, '__len__')


class INATURALIST2018(Dataset):
    """ INATURALIST Pytorch Dataset """
    splits = ['train', 'val', 'test']

    def_supcats = ['Amphibia', 'Animalia', 'Arachnida', 'Aves', 'Fungi',
                   'Insecta', 'Mammalia', 'Mollusca', 'Plantae', 'Reptilia']

    def __init__(self,
                 root=expanduser("~") + "/.avalanche/data/inaturalist2018/",
                 split='train', transform=ToTensor(), target_transform=None,
                 loader=pil_loader, download=True, supcats=None):
        assert split in self.splits
        self.split = split  # training set or test set
        self.transform = transform
        self.target_transform = target_transform
        self.root = root
        self.loader = loader
        self.log = logging.getLogger("avalanche")

        # Supercategories to include (None = all)
        self.supcats = supcats if supcats is not None else self.def_supcats

        if download:
            download_trainval = self.split in ['train', 'val']
            self.core_data = INATURALIST_DATA(data_folder=root,
                                              trainval=download_trainval)

        # load annotations
        ann_file = f'{split}2018.json'
        self.log.info(f'Loading annotations from: {ann_file}')

        with open(os.path.join(root, ann_file)) as data_file:
            data = json.load(data_file)

        # Connect through annotations
        # annotation
        # {
        #     "id": int,
        #     "image_id": int,
        #     "category_id": int
        # }
        self.imgs = []
        self.targets = []
        self.suptargets = []
        self.cats_per_supcat = {}  # Which categories in supercategories to define tasks later
        for ann, img, cat in zip(data['annotations'],
                                 data['images'],
                                 data['categories']):
            img_id = ann["image_id"]
            cat_id = ann["category_id"]
            assert img_id == img["id"]
            assert cat_id == cat["id"]

            target = cat["class"]
            supcat = cat["supercategory"]

            if self.supcats is None or supcat in self.supcats:  # Made selection

                # Add category to supercategory
                if supcat not in self.cats_per_supcat:
                    self.cats_per_supcat[supcat] = set()
                self.cats_per_supcat[supcat].add(target)

                # Add to list
                self.imgs.append(img['file_name'])
                self.targets.append(target)
                self.suptargets.append(supcat)

        cnt_per_supcat = {k: len(v) for k, v in self.cats_per_supcat.items()}
        self.log.info("Classes per supercategories:")
        self.log.info(pprint.pformat(cnt_per_supcat, indent=2))

        self.log.info(f"Images in total: {len(self.targets)}")

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            tuple: (sample, target) where target is class_index of the target
                class.
        """

        target = self.targets[index]
        img = self.loader(os.path.join(self.root, self.imgs[index]))
        # suptarget = self.suptargets[index] # uncomment if required

        if self.transform is not None:
            img = self.transform(img)
        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target

    def __len__(self):
        return len(self.targets)


if __name__ == "__main__":
    # Run from outside this dir as 'python3 -m inaturalist.inaturalist'

    # this litte example script can be used to visualize the first image
    # leaded from the dataset.
    from torch.utils.data.dataloader import DataLoader
    import matplotlib.pyplot as plt
    from torchvision import transforms
    import torch

    train_data = INATURALIST2018(root='/usr/data/delangem/inaturalist2018')
    print("train size: ", len(train_data))
    dataloader = DataLoader(train_data, batch_size=1)

    for batch_data in dataloader:
        x, y = batch_data
        plt.imshow(
            transforms.ToPILImage()(torch.squeeze(x))
        )
        plt.show()
        print(x.size())
        print(len(y))
        break

__all__ = [
    'INATURALIST2018'
]