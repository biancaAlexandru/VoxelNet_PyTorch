import numpy as np
import cv2
import os
# from scipy.misc import imread

import pdb

CAM = 2


def load_velodyne_points(filename):
    # Load data points
    points = np.fromfile(filename, dtype=np.float32).reshape(-1, 4)   # (N, 4); N is around 10k, 4 means [x, y, z, r]

    return points


def load_calib(calib_dir):
    # P2 * R0_rect * Tr_velo_to_cam * y
    lines = open(calib_dir).readlines()
    lines = [line.split()[1:] for line in lines][:-1]

    P = np.array(lines[CAM]).reshape(3, 4)

    Tr_velo_to_cam = np.array(lines[5]).reshape(3, 4)
    Tr_velo_to_cam = np.concatenate([Tr_velo_to_cam, np.array([0, 0, 0, 1]).reshape(1, 4)], 0)

    R_cam_to_rect = np.eye(4)
    R_cam_to_rect[:3, :3] = np.array(lines[4][:9]).reshape(3, 3)

    P = P.astype('float32')
    Tr_velo_to_cam = Tr_velo_to_cam.astype('float32')
    R_cam_to_rect = R_cam_to_rect.astype('float32')

    return P, Tr_velo_to_cam, R_cam_to_rect


def prepare_velo_points(pts3d_raw):
    # Replaces the reflectance value by 1, and tranposes the array,
    # so points can be directly multiplied by the camera projection matrix
    pts3d = pts3d_raw

    # Reflectance > 0
    indices = pts3d[:, 3] > 0
    pts3d = pts3d[indices, :]
    pts3d[:, 3] = 1

    return pts3d.transpose(), indices


def project_velo_points_in_img(pts3d, T_cam_velo, Rrect, Prect):
    # Project 3D points into 2D image. Expects pts3d as a 4xN numpy array.
    # Returns the 2D projection of the points that are in front of the camera only an the corresponding 3D points.

    # 3D points in camera reference frame.
    pts3d_cam = Rrect.dot(T_cam_velo.dot(pts3d))

    # Before projecting, keep only points with z>0 (points that are in front of the camera).
    idx = (pts3d_cam[2, :] >= 0)
    pts2d_cam = Prect.dot(pts3d_cam[:, idx])

    return pts3d[:, idx], pts2d_cam / pts2d_cam[2, :], idx


def align_img_and_pc(img_dir, pc_dir, calib_dir):
    img = cv2.imread(img_dir)
    pts = load_velodyne_points(pc_dir)
    P, Tr_velo_to_cam, R_cam_to_rect = load_calib(calib_dir)

    pts3d, indices = prepare_velo_points(pts)

    reflectances = pts[indices, 3]
    pts3d, pts2d_normed, idx = project_velo_points_in_img(pts3d, Tr_velo_to_cam, R_cam_to_rect, P)

    # Print reflectances.shape, idx.shape
    reflectances = reflectances[idx]

    # Print reflectances.shape, pts3d.shape, pts2d_normed.shape
    assert reflectances.shape[0] == pts3d.shape[1] == pts2d_normed.shape[1]

    rows, cols = img.shape[:2]

    points = []
    for i in range(pts2d_normed.shape[1]):
        c = int(np.round(pts2d_normed[0, i]))
        r = int(np.round(pts2d_normed[1, i]))
        if cols > c > r > 0 and c > 0:
            color = img[r, c, :]
            point = [pts3d[0, i], pts3d[1, i], pts3d[2, i], reflectances[i], color[0], color[1], color[2],
                     pts2d_normed[0, i], pts2d_normed[1, i]]
            points.append(point)

    points = np.array(points)

    return points


if __name__ == '__main__':

    # Update the following directories
    IMG_ROOT = 'D:/BiancaAlexandru/VoxelNet_PyTorch/data/KITTI/image/training/image_2/'
    PC_ROOT = 'D:/BiancaAlexandru/VoxelNet_PyTorch/data/KITTI/point_cloud/training/velodyne/'

    print("In main: {0} {1}".format(IMG_ROOT, os.path.exists(IMG_ROOT)))
    print("In main: {0} {1}".format(PC_ROOT, os.path.exists(PC_ROOT)))
    CALIB_ROOT = 'D:/BiancaAlexandru/VoxelNet_PyTorch/data/KITTI/calib/training/calib/'

    for frame in range(0, 7481):
        img_dir = IMG_ROOT + '%06d.png' % frame
        pc_dir = PC_ROOT + '%06d.bin' % frame
        calib_dir = CALIB_ROOT + '%06d.txt' % frame

        points = align_img_and_pc(img_dir, pc_dir, calib_dir)

        output_name = PC_ROOT + str(frame) + '.bin'
        points[:, :4].astype('float32').tofile(output_name)
        print(output_name)
