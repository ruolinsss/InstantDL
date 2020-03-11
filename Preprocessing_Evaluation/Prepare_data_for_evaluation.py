import os, fnmatch
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Computer Modern Roman"
import glob
from skimage import io
from skimage.io import imread
from skimage.color import gray2rgb, rgb2gray
from skimage.transform import resize
import os

def normalize(data):
	mindata = np.min(data)
	maxdata = np.max(data)
	return (data - mindata) / (maxdata - mindata)

def import_images(import_dir, files, new_file_ending): 
	data = []
	names = []
	#print(import_dir)
	for file in files:
		if new_file_ending is not None:
			file = (file + new_file_ending)
		if file.endswith(".npy"):
			imp = np.array(np.load(os.path.join(import_dir, file)))
		else:
			imp = np.array(imread(os.path.join(import_dir, file)))
		if np.shape(imp)[-1] == 1:
			imp = imp[...,-1]
		if np.shape(imp)[-1] is not 3:
			#print("Gray to RGB")
			imp = gray2rgb(imp)
		#print("import shape", np.shape(imp))
		data.append(imp)
		names.append(file)
	data = np.array(data)
	print("Checking dimensions:")
	if np.shape(data)[-1] == 1:
		data = data[...,0]
	print("Shape of data imported is:", np.shape(data))
	return data, names

def calcerrormap(prediction, groundtruth):
	print(np.shape(groundtruth))
	print(np.shape(prediction))
	groundtruth = np.asarray(groundtruth, dtype=float)
	prediction = np.asarray(prediction, dtype=float)
	groundtruth_norm = (groundtruth - np.mean(groundtruth))/(np.std(groundtruth))
	prediction_norm = (prediction - np.mean(prediction))/(np.std(prediction))
	groundtruth_fs = (groundtruth - np.min(groundtruth))/(np.max(groundtruth)- np.min(groundtruth))
	prediction_fs = (prediction - np.min(prediction))/(np.max(prediction)- np.min(prediction))
	abs_errormap_norm = ((groundtruth_fs - prediction_fs))
	rel_errormap_norm = np.abs(np.divide(abs_errormap_norm, groundtruth_norm, out=np.zeros_like(abs_errormap_norm), where=groundtruth_norm!=0))
	rel_error_norm = np.mean(np.concatenate(np.concatenate((rel_errormap_norm))))
	print("The relative Error over the normalized dataset is:",rel_error_norm, " best ist close to zero")
	return abs_errormap_norm, rel_errormap_norm

def prepare_data_for_evaluation(root_dir, max_images):
	test_dir = root_dir + "test/"
	results_dir = root_dir + "results/"
	report_dir = root_dir + "evaluation"
	insights_dir = root_dir + "insights"
	if os.path.isdir(test_dir + "/image/") == True:
		RCNN = False
	else:
		RCNN = True
	#Set results dir only for RCNN
	results_dir = root_dir + "results/"
	groundtruth_exists = False
	if os.path.exists(root_dir + "/test/groundtruth/") and os.path.isdir(root_dir + "/test/groundtruth/"):
		groundtruth_exists = True
	if RCNN == True:
		print("Resizing MaskRCNN images to 256, 256 dimensins to make them stackable")
		image_fnames = os.listdir(test_dir)
		image_fnames = image_fnames[0:max_images]
		image = []
		groundtruth = []
		predictions = []
		print("importing", len(image_fnames), "files")
		for name in image_fnames:
			image_folder = (test_dir+name+"/image/"+name+".png")
			imagein = (np.array(rgb2gray(io.imread(image_folder))))
			image.append(resize(imagein, (256,256)))
			groundtruths_imp = []
			for file in os.listdir(test_dir + name + "/mask/"):
				groundtruths_in = np.array(io.imread(test_dir + name + "/mask/" + file))
				groundtruths_in = resize(rgb2gray(groundtruths_in), (256, 256))
				groundtruths_imp.append(groundtruths_in)
			groundtruth.append(np.sum(groundtruths_imp, axis=0))
			prediction_folder = results_dir + name + ".npy"
			prediction = np.load(prediction_folder)
			prediction = np.sum(np.where(prediction == 1, 1, 0), axis = -1)
			prediction[prediction > 1] = 1
			predictions.append(resize(prediction, (256,256)))
		print("pred", np.shape(predictions))
		print("gt", np.shape(groundtruth))
		abs_errormap_norm, rel_errormap_norm = calcerrormap(predictions, groundtruth)

	else:
		image_files = os.listdir(os.path.join(test_dir, "image/"))
		if max_images is not None:
			image_files = image_files[0: max_images]
		image, image_fnames = import_images(test_dir + "/image/", image_files, None)
		predictions, predictions_fnames = import_images(results_dir, image_files, "_predict.tif")
		if os.path.isdir(test_dir + "/groundtruth/"):
			groundtruth, groundtruth_fnames = import_images(test_dir + "/groundtruth/", image_files, None)
		image, image_fnames = import_images(test_dir + "/image/", image_files, None)
		if os.path.isdir(test_dir + "image2"):
			image2, image2_fnames = import_images(test_dir + "image2", image_files, None)
			image1, image1_fnames = import_images(test_dir + "image1", image_files, None)
		elif os.path.isdir(test_dir + "image1"):
			image1, image1_fnames = import_images(test_dir + "image1", image_files, None)
	if os.path.isdir(root_dir + "uncertainty"): 
		uncertainty, uncertainty_fnames = import_images(root_dir + "uncertainty", image_files, "_predict.tif")
	if os.path.isdir(test_dir + "/groundtruth/"):
		abs_errormap_norm, rel_errormap_norm = calcerrormap(predictions, groundtruth)

	os.makedirs(root_dir + "/insights/", exist_ok=True)
	np.save(root_dir + "/insights/" + "image", image)
	np.save(root_dir + "/insights/" + "prediction", predictions)
	if len(groundtruth) > 1:
		np.save(root_dir + "/insights/" + "groundtruth", groundtruth)
		np.save(root_dir + "/insights/" + "abs_errormap", abs_errormap_norm)
		np.save(root_dir + "/insights/" + "rel_errormap", rel_errormap_norm)
	np.save(root_dir + "/insights/" + "image_names", image_fnames)
	if os.path.isdir(root_dir + "uncertainty"):
		np.save(root_dir + "/insights/" + "uncertainty", normalize(uncertainty))
	if os.path.isdir(test_dir + "image1"):
		print("Two")
		np.save(root_dir + "/insights/" + "image1", image1)
	if os.path.isdir(test_dir + "image2"):
		print("Three")
		np.save(root_dir + "/insights/" + "image1", image1)
		np.save(root_dir + "/insights/" + "image2", image2)
