# -*- coding: utf-8 -*-
"""Grad-CAM for the MobileNetV3-Small plant-disease classifier.

Grad-CAM (Selvaraju et al., 2017) weights each feature map A^k of the last
convolutional block by the spatial mean of d y^c / d A^k, sums the weighted
maps and keeps the positive part. The resulting coarse map is resized to the
input image and blended over it as a heatmap.
"""
import torch
from matplotlib import colormaps
from PIL import Image


class GradCAM(object):
    def __init__(self, model, target_layer=None):
        self.model = model
        self.layer = target_layer if target_layer is not None else model.features[-1]
        self._acts = None
        self._grads = None
        self.layer.register_forward_hook(self._save_acts)
        self.layer.register_full_backward_hook(self._save_grads)

    def _save_acts(self, _module, _inp, out):
        self._acts = out.detach()

    def _save_grads(self, _module, _gin, gout):
        self._grads = gout[0].detach()

    def __call__(self, x, class_idx=None):
        """Return (cam[H', W'] in 0..1, probabilities[C]) for one image tensor."""
        self.model.zero_grad(set_to_none=True)
        with torch.enable_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)[0].detach()
            if class_idx is None:
                class_idx = int(probs.argmax())
            logits[0, class_idx].backward()
        weights = self._grads.mean(dim=(2, 3), keepdim=True)          # alpha_k^c
        cam = torch.relu((weights * self._acts).sum(dim=1))[0]        # ReLU(sum_k)
        cam = cam - cam.min()
        if float(cam.max()) > 0:
            cam = cam / cam.max()
        return cam, probs


def overlay(img, cam, alpha=0.45):
    """Blend a 0..1 CAM over a PIL RGB image using the 'jet' colour map."""
    w, h = img.size
    cam_img = Image.fromarray(
        (cam.mul(255).byte().cpu().numpy()), mode="L").resize((w, h), Image.BILINEAR)
    jet = colormaps["jet"]
    lut = [tuple(int(255 * v) for v in jet(i / 255.0)[:3]) for i in range(256)]
    heat = Image.new("RGB", (w, h))
    heat.putdata([lut[p] for p in cam_img.getdata()])
    return Image.blend(img.convert("RGB"), heat, alpha)
