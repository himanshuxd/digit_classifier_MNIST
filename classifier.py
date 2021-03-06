#!/usr/bin/env python

import numpy as np
import pandas as pd

import tensorflow as tf

print(tf.__version__)

conv2d = tf.nn.conv2d 

# Parameters
LEARNING_RATE = 0.001
TRAINING_EPOCHS = 3000
BATCH_SIZE = 100
DISPLAY_STEP = 10
DROPOUT_CONV = 0.8
DROPOUT_HIDDEN = 0.6
VALIDATION_SIZE = 2000      # Set to 0 to train on all available data

# Read MNIST data set (Train data from CSV file)
data = pd.read_csv('./all/train.csv')

# Extracting images and labels from given data
# For images
images = data.iloc[:,1:].values
images = images.astype(np.float)

# For labels
# Got error :
# labels_flat = data[[0]].values.ravel()
labels_flat = data.iloc[:,0].values.ravel()
labels_count = np.unique(labels_flat).shape[0]

def dense_to_one_hot(labels_dense, num_classes):
    num_labels = labels_dense.shape[0]
    index_offset = np.arange(num_labels) * num_classes
    labels_one_hot = np.zeros((num_labels, num_classes))
    labels_one_hot.flat[index_offset + labels_dense.ravel()] = 1
    return labels_one_hot

labels = dense_to_one_hot(labels_flat, labels_count)
labels = labels.astype(np.uint8)

# Normalize from [0:255] => [0.0:1.0]
images = np.multiply(images, 1.0 / 255.0)
image_size = images.shape[1]
image_width = image_height = np.ceil(np.sqrt(image_size)).astype(np.uint8)

# Split data into training & validation
validation_images = images[:VALIDATION_SIZE]
validation_labels = labels[:VALIDATION_SIZE]

train_images = images[VALIDATION_SIZE:]
train_labels = labels[VALIDATION_SIZE:]

# Create Input and Output
X = tf.placeholder('float', shape=[None, image_size])       # mnist data image of shape 28*28=784
Y_gt = tf.placeholder('float', shape=[None, labels_count])    # 0-9 digits recognition => 10 classes

# Weight initialization
def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial)

# Weight initialization (Xavier's init)
def weight_xavier_init(n_inputs, n_outputs, uniform=True):
    if uniform:
        init_range = tf.sqrt(6.0 / (n_inputs + n_outputs))
        return tf.random_uniform_initializer(-init_range, init_range)
    else:
        stddev = tf.sqrt(3.0 / (n_inputs + n_outputs))
        return tf.truncated_normal_initializer(stddev=stddev)

# Bias initialization
def bias_variable(shape):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)

# Model Parameters
W1 = tf.get_variable("W1", shape=[5, 5, 1, 32], initializer=weight_xavier_init(5*5*1, 32))
W2 = tf.get_variable("W2", shape=[5, 5, 32, 64], initializer=weight_xavier_init(5*5*32, 64))
W3_FC1 = tf.get_variable("W3_FC1", shape=[64*7*7, 1024], initializer=weight_xavier_init(64*7*7, 1024))
W4_FC2 = tf.get_variable("W4_FC2", shape=[1024, labels_count], initializer=weight_xavier_init(1024, labels_count))

B1 = bias_variable([32])
B2 = bias_variable([64])
B3_FC1 = bias_variable([1024])
B4_FC2 = bias_variable([labels_count])

drop_conv = tf.placeholder('float')
drop_hidden = tf.placeholder('float')

# CNN model
X1 = tf.reshape(X, [-1,image_width , image_height,1])                   # shape=(?, 28, 28, 1)
    
# Layer 1
l1_conv = tf.nn.relu(conv2d(X1, W1) + B1)                               # shape=(?, 28, 28, 32)
l1_pool = max_pool_2x2(l1_conv)                                         # shape=(?, 14, 14, 32)
l1_drop = tf.nn.dropout(l1_pool, drop_conv)

# Layer 2
l2_conv = tf.nn.relu(conv2d(l1_drop, W2)+ B2)                           # shape=(?, 14, 14, 64)
l2_pool = max_pool_2x2(l2_conv)                                         # shape=(?, 7, 7, 64)
l2_drop = tf.nn.dropout(l2_pool, drop_conv) 

# Layer 3 - FC1
l3_flat = tf.reshape(l2_drop, [-1, W3_FC1.get_shape().as_list()[0]])    # shape=(?, 1024)
l3_feed = tf.nn.relu(tf.matmul(l3_flat, W3_FC1)+ B3_FC1) 
l3_drop = tf.nn.dropout(l3_feed, drop_hidden)


# Layer 4 - FC2
Y_pred = tf.nn.softmax(tf.matmul(l3_drop, W4_FC2)+ B4_FC2)              # shape=(?, 10)

# Cost function and training 
cost = -tf.reduce_sum(Y_gt*tf.log(Y_pred))
regularizer = (tf.nn.l2_loss(W3_FC1) + tf.nn.l2_loss(B3_FC1) + tf.nn.l2_loss(W4_FC2) + tf.nn.l2_loss(B4_FC2))
cost += 5e-4 * regularizer

#train_op = tf.train.AdamOptimizer(LEARNING_RATE).minimize(cost)
train_op = tf.train.RMSPropOptimizer(LEARNING_RATE, 0.9).minimize(cost)
correct_predict = tf.equal(tf.argmax(Y_pred, 1), tf.argmax(Y_gt, 1))
accuracy = tf.reduce_mean(tf.cast(correct_predict, 'float'))
predict = tf.argmax(Y_pred, 1)

epochs_completed = 0
index_in_epoch = 0
num_examples = train_images.shape[0]

# start TensorFlow session
init = tf.initialize_all_variables()
sess = tf.InteractiveSession()

sess.run(init)

# visualisation variables
train_accuracies = []
validation_accuracies = []

DISPLAY_STEP=1

for i in range(TRAINING_EPOCHS):

    #get new batch
    batch_xs, batch_ys = next_batch(BATCH_SIZE)        

    # check progress on every 1st,2nd,...,10th,20th,...,100th... step
    if i%DISPLAY_STEP == 0 or (i+1) == TRAINING_EPOCHS:
        
        train_accuracy = accuracy.eval(feed_dict={X:batch_xs, 
                                                  Y_gt: batch_ys,
                                                  drop_conv: DROPOUT_CONV, 
                                                  drop_hidden: DROPOUT_HIDDEN})       
        if(VALIDATION_SIZE):
            validation_accuracy = accuracy.eval(feed_dict={ X: validation_images[0:BATCH_SIZE], 
                                                            Y_gt: validation_labels[0:BATCH_SIZE],
                                                            drop_conv: DROPOUT_CONV, drop_hidden: DROPOUT_HIDDEN})                                  
            print('training_accuracy / validation_accuracy => %.2f / %.2f for step %d'%(train_accuracy, validation_accuracy, i))
            
            validation_accuracies.append(validation_accuracy)
            
        else:
             print('training_accuracy => %.4f for step %d'%(train_accuracy, i))
        train_accuracies.append(train_accuracy)
        
        # increase DISPLAY_STEP
        if i%(DISPLAY_STEP*10) == 0 and i:
            DISPLAY_STEP *= 10
    # train on batch
    sess.run(train_op, feed_dict={X: batch_xs, Y_gt: batch_ys, drop_conv: DROPOUT_CONV, drop_hidden: DROPOUT_HIDDEN})


# check final accuracy on validation set  
if(VALIDATION_SIZE):
    validation_accuracy = accuracy.eval(feed_dict={X: validation_images, 
                                                   Y_gt: validation_labels,
                                                   drop_conv: DROPOUT_CONV, drop_hidden: DROPOUT_HIDDEN})
    print('validation_accuracy => %.4f'%validation_accuracy)

# read test data from CSV file 
test_images = pd.read_csv('./all/test.csv').values
test_images = test_images.astype(np.float)

# convert from [0:255] => [0.0:1.0]
test_images = np.multiply(test_images, 1.0 / 255.0)

print('test_images({0[0]},{0[1]})'.format(test_images.shape))


# predict test set
#predicted_lables = predict.eval(feed_dict={X: test_images, keep_prob: 1.0})

# using batches is more resource efficient
predicted_lables = np.zeros(test_images.shape[0])
for i in range(0,test_images.shape[0]//BATCH_SIZE):
    predicted_lables[i*BATCH_SIZE : (i+1)*BATCH_SIZE] = predict.eval(feed_dict={X: test_images[i*BATCH_SIZE : (i+1)*BATCH_SIZE], drop_conv: 1.0, drop_hidden: 1.0})


# save results
np.savetxt('submission.csv', 
           np.c_[range(1,len(test_images)+1),predicted_lables], 
           delimiter=',', 
           header = 'ImageId,Label', 
           comments = '', 
           fmt='%d')

sess.close()

