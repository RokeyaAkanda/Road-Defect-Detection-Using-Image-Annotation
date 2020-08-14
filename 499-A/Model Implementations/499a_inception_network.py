# -*- coding: utf-8 -*-
"""499A Inception network.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11ezWI7kbmw8HLhwch04Ng1ZQPR_Ld-xz
"""

!pip install -U -q PyDrive

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials
# Authenticating and creating the Drive client
auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

df = drive.CreateFile({'id': '1fsAmPhxeKkmbGP8ymW6DImPg-ZgifdLU'})
df.GetContentFile('roads.zip')
!unzip roads.zip

import glob

bad_img = glob.glob('roads/bad/*.*')
good_img = glob.glob('roads/good/*.*')

Y = []
for i in bad_img:
  Y.append(0)

for i in good_img:
  Y.append(1)

classes=Y # saving classes to apply stratified cross-validation later

import numpy as np
Y=np.asarray(Y)

import pandas as pd
Y = pd.get_dummies(Y).to_numpy()
Y.shape

imgg_arr=[]
import tensorflow as tf
for i in bad_img:
    image=tf.keras.preprocessing.image.load_img(i, color_mode='rgb', target_size=None)
    image=np.array(image)
    imgg_arr.append(image)

for i in good_img:
    image=tf.keras.preprocessing.image.load_img(i, color_mode='rgb', target_size=None)
    image=np.array(image)
    imgg_arr.append(image)

#deciding pixel values from image samples
#def pixel_decider(arr): 
 # count_1=0
 # count_2=0
 # count=0
 # for i in imgg_arr:
 #   count=count+1
 #   f_pixel=int(i.shape[0])
 #   count_1=count_1+f_pixel   # returns average pixel values from sample set.
 #   s_pixel=int(i.shape[1])   # This method needs very high computational power when the sample set has large pixel values.
 #   count_2=count_2+s_pixel
 # count_1=int(count_1/count)
 # count_2=int(count_2/count)  
 # return count_1,count_2

#deciding pixel values from image samples
def pixel_decider(arr): 
	f_pixel=int(arr[0].shape[0])
	s_pixel=int(arr[0].shape[1])
	for i in arr:                    # returns minimum pixel values from sample set.
		if f_pixel > (i+1).shape[0]:
			f_pixel=int((i+1).shape[0])
		if s_pixel > (i+1).shape[1]:
			s_pixel=int((i+1).shape[1])
	return f_pixel,s_pixel

first_pixel,second_pixel=pixel_decider(imgg_arr) #calling method
print("first pixel:",first_pixel)
print("second pixel:",second_pixel)

#now resizing image samples
from skimage.transform import resize
ImgArray=[]
for i in imgg_arr:
  resized_img = resize(i,(first_pixel,second_pixel))
  ImgArray.append(resized_img.astype('float32'))

ImgArray=np.asarray(ImgArray)

ImgArray.shape

def Img_Augmentor(Img_Array,Y_Array,num_of_Img,num_of_aug): # Augmentation method
  
  from keras.preprocessing.image import ImageDataGenerator
  datagen = ImageDataGenerator(rotation_range=40,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest') 
  
  # random index generator
  indx_arr=[]        
  from random import randint
  for _ in range(num_of_Img):
	  value = randint(0, len(Img_Array)-1)
	  indx_arr.append(value)
  selected_img=Img_Array[indx_arr] # randomly selected image

  agg=[] # augmented Image array
  for i in selected_img:
    aaa=i.reshape((1,)+i.shape)
    aug_d=datagen.flow(aaa)
    aug_img=[next(aug_d)[0].astype(np.float32) for i in range(num_of_aug)]
    for j in range(0,len(aug_img)):
      agg.append(aug_img[j])

  agg=np.asarray(agg) # (3000, 48, 48, 3)

  #merging augmented image with normal image
  Img_Array=np.array(Img_Array)
  augmented_image=np.array(agg)
  new_Img_Arr=np.append(Img_Array,augmented_image,axis=0)
  #new_Img_Arr=np.around(new_Img_Arr, decimals=3) # 3 decimal point
 
  ## preparing Y_train
  Y_new=Y_Array
  y_tmp=Y_Array[indx_arr]
  keep_y=[] # copying original Y_train to keep_y
  for i in Y_new:
    keep_y.append(i)
  for i in y_tmp: # merging original Y and augmented Y
    for j in range(0,(num_of_aug)):
      keep_y.append(i)
  new_y_Arr=np.asarray(keep_y)  
    
  return new_Img_Arr,new_y_Arr,indx_arr  # Method ends

augmented_x,augmented_y,photo_indexes=Img_Augmentor(ImgArray,Y,100,2) #method call

augmented_x.shape

augmented_y.shape

classes=np.asarray(classes)  # preparing class values from cross-validation
values=classes[photo_indexes]
values=np.asarray(values)

tmp_arr=[]
for i in values:  # adjusting class values
  for j in range(0,2):
    tmp_arr.append(i)
tmp_arr=np.asarray(tmp_arr)

tmp_arr.shape

my_classes=np.append(classes,tmp_arr,axis=0) #merging old classes and new classes

my_classes.shape

# creating the network
from keras.models import Model
from keras.layers import Input
from keras.layers import Conv2D
from keras.layers import MaxPooling2D,Flatten,Dense
from keras.layers.merge import concatenate
from keras.utils import plot_model
 
# function for creating a projected inception module
def inception_module(layer_in, f1, f2_in, f2_out, f3_in, f3_out, f4_out):
	#1x1 conv
	conv1 = Conv2D(f1, (1,1), padding='same', activation='relu')(layer_in)
	# 3x3 conv
	conv3 = Conv2D(f2_in, (1,1), padding='same', activation='relu')(layer_in)
	conv3 = Conv2D(f2_out, (3,3), padding='same', activation='relu')(conv3)
	# 5x5 conv
	conv5 = Conv2D(f3_in, (1,1), padding='same', activation='relu')(layer_in)
	conv5 = Conv2D(f3_out, (5,5), padding='same', activation='relu')(conv5)
	# 3x3 max pooling
	pool = MaxPooling2D((3,3), strides=(1,1), padding='same')(layer_in)
	pool = Conv2D(f4_out, (1,1), padding='same', activation='relu')(pool)
	#concatenate layer
	concated_layer = concatenate([conv1, conv3, conv5, pool], axis=-1)
	#creating output shape
	pooling=MaxPooling2D(pool_size=(2, 2))(concated_layer)
	flattened = Flatten()(pooling)
	fully_connected = Dense(2, activation='softmax')(flattened)
	return fully_connected

                                                                       # For 1 inception block
# define model input
visible = Input(shape=(first_pixel, second_pixel, 3))
# add inception block 1
layer = inception_module(visible, 32, 64, 64, 16, 32, 32)
# create model
model = Model(inputs=visible, outputs=layer)
# summarize model
model.summary()
# plot model architecture
plot_model(model, show_shapes=True, to_file='inception_module.png')

from keras.losses import categorical_crossentropy
from keras.optimizers import Adam
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

augmented_y = augmented_y.astype(int)

# Training the model using K=5 fold cross-validation
Predict_list=[]
from sklearn.model_selection import KFold
from sklearn.model_selection import StratifiedKFold
from sklearn import metrics
fold=0
kf = StratifiedKFold(n_splits=5, random_state=None, shuffle=False)
for train_index, test_index in kf.split(augmented_x,my_classes):
   fold+=1
   print("Fold:",fold," ","TRAIN:", train_index, "TEST:", test_index)
   X_train, X_test = augmented_x[train_index], augmented_x[test_index]
   y_train, y_test = augmented_y[train_index], augmented_y[test_index]
   model.fit(X_train,y_train,batch_size=15,epochs=10,verbose=1, validation_data=(X_test,y_test))
   score=model.evaluate(X_test, y_test, verbose=0)
   Predict_list.append(score)

print(Predict_list)

accuracy=0
for i in Predict_list:
  accuracy=accuracy+i[1]
accuracy=accuracy / 5   #as k=5 fold

print("Accuracy: %.2f%%" % (accuracy*100))

# creating the network
from keras.models import Model
from keras.layers import Input
from keras.layers import Conv2D
from keras.layers import MaxPooling2D,Flatten,Dense
from keras.layers.merge import concatenate
from keras.utils import plot_model
 
# function for creating a projected inception module
def inception_module(layer_in, f1, f2_in, f2_out, f3_in, f3_out, f4_out):
	#1x1 conv
	conv1 = Conv2D(f1, (1,1), padding='same', activation='relu')(layer_in)
	# 3x3 conv
	conv3 = Conv2D(f2_in, (1,1), padding='same', activation='relu')(layer_in)
	conv3 = Conv2D(f2_out, (3,3), padding='same', activation='relu')(conv3)
	# 5x5 conv
	conv5 = Conv2D(f3_in, (1,1), padding='same', activation='relu')(layer_in)
	conv5 = Conv2D(f3_out, (5,5), padding='same', activation='relu')(conv5)
	# 3x3 max pooling
	pool = MaxPooling2D((3,3), strides=(1,1), padding='same')(layer_in)
	pool = Conv2D(f4_out, (1,1), padding='same', activation='relu')(pool)
	#concatenate layer
	concated_layer = concatenate([conv1, conv3, conv5, pool], axis=-1)
	return concated_layer

                                                                          # For 2 inception block
# define model input
visible = Input(shape=(first_pixel, second_pixel, 3))
# add inception block 1
layer = inception_module(visible, 16, 32, 32, 16, 32, 32)
# add inception block 2
layer = inception_module(layer, 16, 16, 32, 32, 64, 64)
#creating output shape
pooling=MaxPooling2D(pool_size=(2, 2),strides=(2, 2))(layer)
flattened = Flatten()(pooling)
fully_connected = Dense(2, activation='softmax')(flattened)
# create model
model = Model(inputs=visible, outputs=fully_connected)
# summarize model
model.summary()
# plot model architecture
plot_model(model, show_shapes=True, to_file='inception_module.png')

from keras.losses import categorical_crossentropy
from keras.optimizers import Adam
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Training the model using K=5 fold cross-validation
Predict_list=[]
from sklearn.model_selection import KFold
from sklearn.model_selection import StratifiedKFold
from sklearn import metrics
fold=0
kf = StratifiedKFold(n_splits=5, random_state=None, shuffle=False)
for train_index, test_index in kf.split(augmented_x,my_classes):
   fold+=1
   print("Fold:",fold," ","TRAIN:", train_index, "TEST:", test_index)
   X_train, X_test = augmented_x[train_index], augmented_x[test_index]
   y_train, y_test = augmented_y[train_index], augmented_y[test_index]
   model.fit(X_train,y_train,batch_size=10,epochs=10,verbose=1, validation_data=(X_test,y_test))
   score=model.evaluate(X_test, y_test, verbose=0)
   Predict_list.append(score)

print(Predict_list)

accuracy=0
for i in Predict_list:
  accuracy=accuracy+i[1]
accuracy=accuracy / 5   #as k=5 fold

print("Accuracy: %.2f%%" % (accuracy*100))

# testing a single photo from test set
photo_test=X_test[59]

from skimage.io import imread, imshow
import matplotlib.pyplot as plt
imshow(photo_test)
print("Actual Image.")

model.predict(X_test[59:60]) # model predicts this image as [0, 1] 
                           # because probability is high in the second position [0.0000094%,  99.99%]

y_test[59:60]   # this is actual true value [0, 1].