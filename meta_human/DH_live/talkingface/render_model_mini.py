import torch
import numpy as np
from .data.few_shot_dataset import select_ref_index
device = "cuda" if torch.cuda.is_available() else "cpu"
import cv2

from .utils import draw_mouth_maps

class RenderModel_Mini:
    def __init__(self):
        self.__net = None

    def loadModel(self, ckpt_path):
        from .models.DINet_mini import DINet_mini_pipeline as DINet
        n_ref = 3
        source_channel = 3
        ref_channel = n_ref * 4
        self.net = DINet(source_channel, ref_channel).to(device)
        checkpoint = torch.load(ckpt_path, map_location=torch.device(device))
        net_g_static = checkpoint['state_dict']['net_g']
        self.net.infer_model.load_state_dict(net_g_static)
        self.net.eval()


    def reset_charactor(self, img_list, driven_keypoints, standard_size = 256):
        ref_img_index_list = select_ref_index(driven_keypoints, n_ref=3, ratio=0.33)  # 从当前视频选n_ref个图片
        ref_img_list = []
        for i in ref_img_index_list:
            ref_face_edge = draw_mouth_maps(driven_keypoints[i], size=(standard_size, standard_size))
            ref_img = img_list[i]
            ref_face_edge = cv2.resize(ref_face_edge, (128, 128))
            ref_img = cv2.resize(ref_img, (128, 128))
            w_pad = int((128 - 72) / 2)
            h_pad = int((128 - 56) / 2)

            ref_img = np.concatenate([ref_img[h_pad:-h_pad, w_pad:-w_pad], ref_face_edge[h_pad:-h_pad, w_pad:-w_pad, :1]], axis=2)
            # cv2.imshow("ss", ref_img[:,:,::-1])
            # cv2.waitKey(-1)
            ref_img_list.append(ref_img)
        self.ref_img = np.concatenate(ref_img_list, axis=2)

        ref_tensor = torch.from_numpy(self.ref_img / 255.).float().permute(2, 0, 1).unsqueeze(0)

        self.net.ref_input(ref_tensor)


    def interface(self, source_tensor, gl_tensor):
        '''

        Args:
            source_tensor: [batch, 3, 128, 128]
            gl_tensor: [batch, 3, 128, 128]

        Returns:
            warped_img: [batch, 3, 128, 128]
        '''
        warped_img = self.net.interface(source_tensor, gl_tensor)
        return warped_img

    def save(self, path):
        torch.save(self.net.state_dict(), path)