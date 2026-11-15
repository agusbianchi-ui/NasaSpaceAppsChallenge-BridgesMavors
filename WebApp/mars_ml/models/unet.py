"""Minimal U-Net definition used by the supervised segmentation adapter.

PyTorch is imported lazily through ``build_unet`` so the rest of the package can
run without the training extra installed. No trained weights live here.
"""

from __future__ import annotations

from typing import Any


def build_unet(
    *,
    input_channels: int = 1,
    output_channels: int = 1,
    base_channels: int = 32,
) -> Any:
    """Build a small U-Net for binary dune masks.

    The architecture is intentionally modest so it can be trained on a laptop.
    Inputs are expected to be reflectance-like float arrays normalized to
    roughly ``[0, 1]``. Outputs are logits.
    """

    if input_channels < 1 or output_channels < 1:
        raise ValueError("Channel counts must be positive.")
    if base_channels < 8:
        raise ValueError("base_channels must be at least 8.")

    try:
        import torch
        from torch import nn
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "PyTorch is not installed. Install mars_ml/requirements-training.txt "
            "before building the U-Net."
        ) from exc

    class DoubleConv(nn.Module):
        def __init__(self, in_channels: int, out_channels: int) -> None:
            super().__init__()
            self.block = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            )

        def forward(self, x: Any) -> Any:
            return self.block(x)

    class UNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            c = base_channels
            self.enc1 = DoubleConv(input_channels, c)
            self.enc2 = DoubleConv(c, c * 2)
            self.enc3 = DoubleConv(c * 2, c * 4)
            self.enc4 = DoubleConv(c * 4, c * 8)
            self.pool = nn.MaxPool2d(2)
            self.bottleneck = DoubleConv(c * 8, c * 16)
            self.up4 = nn.ConvTranspose2d(c * 16, c * 8, kernel_size=2, stride=2)
            self.dec4 = DoubleConv(c * 16, c * 8)
            self.up3 = nn.ConvTranspose2d(c * 8, c * 4, kernel_size=2, stride=2)
            self.dec3 = DoubleConv(c * 8, c * 4)
            self.up2 = nn.ConvTranspose2d(c * 4, c * 2, kernel_size=2, stride=2)
            self.dec2 = DoubleConv(c * 4, c * 2)
            self.up1 = nn.ConvTranspose2d(c * 2, c, kernel_size=2, stride=2)
            self.dec1 = DoubleConv(c * 2, c)
            self.head = nn.Conv2d(c, output_channels, kernel_size=1)

        def forward(self, x: Any) -> Any:
            e1 = self.enc1(x)
            e2 = self.enc2(self.pool(e1))
            e3 = self.enc3(self.pool(e2))
            e4 = self.enc4(self.pool(e3))
            b = self.bottleneck(self.pool(e4))
            d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
            d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
            d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
            d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
            return self.head(d1)

    return UNet()
