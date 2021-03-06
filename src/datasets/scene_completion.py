"""Scene Completion Using Millions of Photographs Dataset

- http://graphics.cs.cmu.edu/projects/scene-completion/
- James Hays, Alexei A. Efros. Scene Completion Using Millions of Photographs. ACM Transactions on Graphics (SIGGRAPH 2007). August 2007, vol. 26, No. 3.
"""
import zipfile
from pathlib import Path
from typing import Any, Dict

import cv2
import toml
import numpy as np
import torch
from torch.utils.data import Dataset
from src.datasets.utils import download_raw_dataset

METADATA_FILENAME = Path("data/raw/scene_completion/metadata.toml")
DL_DATA_DIRNAME = Path("data/downloaded/scene_completion")
PROCESSED_DATA_DIRNAME = DL_DATA_DIRNAME / "processed"


class SceneCompletionDataset(Dataset):
    def __init__(self, root_dir=PROCESSED_DATA_DIRNAME) -> None:
        self._prepare_data()

        # Get list of all image names
        img_dir = Path(root_dir)
        self.img_paths = [p for p in img_dir.iterdir() if p.stem[-4:] != "mask"]

        assert (
            len(self.img_paths) == 51
        ), "Incorrect expected number of images in dataset!"

    def _prepare_data(self) -> None:
        if not PROCESSED_DATA_DIRNAME.exists():
            metadata = toml.load(METADATA_FILENAME)
            # Download dataset
            download_raw_dataset(metadata, DL_DATA_DIRNAME)

            # Process downloaded dataset
            print("Unzipping Scene Completion...")
            zip = zipfile.ZipFile(DL_DATA_DIRNAME / metadata["filename"])
            PROCESSED_DATA_DIRNAME.mkdir(parents=True, exist_ok=True)
            zip.extractall(PROCESSED_DATA_DIRNAME)
            zip.close()

    def __getitem__(self, idx) -> Dict[str, Any]:
        """
        Returns
        -------
        Dict[str, Any]
            img : torch.ByteTensor
                [C, H, W], range [0, 255]
            label : int
                One of {0, 1}. No meaningful labels for this dataset (all manipulated)
            map : np.ndarray (uint8)
                [H, W], values one of {0, 1}
        """
        img_path = self.img_paths[idx]

        # Get image
        img = cv2.imread(str(img_path))[:, :, [2, 1, 0]]  # [H, W, C]
        assert img.dtype == np.uint8, "Image should be of type int!"
        assert (
            img.min() >= 0 and img.max() <= 255
        ), "Image should be bounded between [0, 255]!"

        img = torch.from_numpy(img).permute(2, 0, 1)  # [C, H, W]

        # Get localization map
        img_name = img_path.stem
        img_ext = img_path.suffix

        map_path = img_path.parent / f"{img_name}_mask{img_ext}"
        # HACK
        if not map_path.is_file():
            # Correct extension
            map_path = img_path.parent / f"{img_name}_mask.jpg"

        map = cv2.imread(str(map_path), cv2.IMREAD_GRAYSCALE)
        assert map.dtype == np.uint8, "Ground-truth should be of type int!"
        assert (
            map.min() >= 0 and map.max() <= 255
        ), "Ground-truth should be bounded between [0, 255]!"

        map[map > 0] = 1

        return {"img": img, "label": 1, "map": map}

    def __len__(self):
        return len(self.img_paths)