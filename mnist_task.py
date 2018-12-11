from __future__ import absolute_import
from __future__ import division
from __future__	import print_function

import numpy as np
import tensorflow as tf

from eunn import EUNNCell

import random

from random import shuffle
from tensorflow.examples.tutorials.mnist import input_data

random.seed(2017)


tf.app.flags.DEFINE_string(
    'model', 'eunn', 'The name of the RNN model: eunn, lstm')

tf.app.flags.DEFINE_integer(
    'iter', 10000, 'training iteration')

tf.app.flags.DEFINE_integer(
    'batch_size', 128, 'The number of samples in each batch.')

tf.app.flags.DEFINE_integer(
    'hidden_size', 128,  'Hidden size of the RNN model')

tf.app.flags.DEFINE_integer(
    'capacity', 4, 'Capacity of uniary matrix in tunable case')

tf.app.flags.DEFINE_boolean(
    'complex', True, 
    'Whether to use complex version. False means changing to orthogonal matrix')

tf.app.flags.DEFINE_boolean(
    'fft', False, 
    'Whether to use fft version. False means using tunable version')


FLAGS = tf.app.flags.FLAGS


def mnist_data(iterator, batch_size, ind, dataset):

	if dataset == "train":
		xx, yy = iterator.train.next_batch(batch_size)
	elif dataset == "validation": 
		xx, yy = iterator.validation.next_batch(batch_size)
	elif dataset == "test": 
		xx, yy = iterator.test.next_batch(batch_size)

	step1 = np.array(xx)
	step2 = np.transpose(step1)
	step3 = [step2[i] for i in ind]
	xx = np.transpose(step3)

	x = []
	y = []
	for i in range(batch_size):
		x.append(xx[i].reshape((28*28, 1)))
		y.append(yy[i])
	
	shuffle_list = list(range(batch_size))
	shuffle(shuffle_list)
	
	x = np.array([x[i] for i in shuffle_list])
	y = np.array([y[i] for i in shuffle_list]).astype(np.int64)

	return x, y

def main(_):

	# --- Set data params ----------------
	n_input = 1
	n_output = 10
	n_train = FLAGS.iter * FLAGS.batch_size
	n_val = 5000
	n_test = 10000

	n_steps = 28 * 28
	n_classes = 10




	# --- Create graph and compute gradients ----------------------
	x = tf.placeholder("float", [None, n_steps, n_input])
	y = tf.placeholder("int64", [None])
	

	# --- Input to hidden layer ----------------------
	if FLAGS.model == "lstm":
		cell = tf.nn.rnn_cell.BasicLSTMCell(FLAGS.hidden_size, state_is_tuple=True, forget_bias=1)
		hidden_out, _ = tf.nn.dynamic_rnn(cell, x, dtype=tf.float32)
	elif FLAGS.model == "eunn":
			cell = EUNNCell(FLAGS.hidden_size, FLAGS.capacity, FLAGS.fft, FLAGS.complex)
			if complex:
					initial_state_re = tf.get_variable('init_state_re', shape=[FLAGS.hidden_size])
					initial_state_im = tf.get_variable('init_state_im', shape=[FLAGS.hidden_size])
					initial_state = tf.complex(initial_state_re, initial_state_im)
					hidden_out_comp, _ = tf.nn.dynamic_rnn(cell, x, dtype=tf.complex64)
					hidden_out = tf.real(hidden_out_comp)
			else:
					initial_state = tf.get_variable('init_state', shape=[FLAGS.hidden_size])
					hidden_out, _ = tf.nn.dynamic_rnn(cell, x, dtype=tf.float32, initial_state=initial_state)

	# --- Hidden Layer to Output ----------------------
	V_init_val = np.sqrt(6.)/np.sqrt(n_output + n_input)

	V_weights = tf.get_variable("V_weights", shape = [FLAGS.hidden_size, n_classes], \
			dtype=tf.float32, initializer=tf.random_uniform_initializer(-V_init_val, V_init_val))
	V_bias = tf.get_variable("V_bias", shape=[n_classes], \
			dtype=tf.float32, initializer=tf.constant_initializer(0.01))

	hidden_out_list = tf.unstack(hidden_out, axis=1)
	temp_out = tf.matmul(hidden_out_list[-1], V_weights)
	output_data = tf.nn.bias_add(temp_out, V_bias) 
	
	cost = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=output_data, labels=y))
	correct_pred = tf.equal(tf.argmax(output_data, 1), y)
	accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))



	# --- Initialization --------------------------------------------------
	optimizer = tf.train.RMSPropOptimizer(learning_rate=0.0001, decay=0.9).minimize(cost)
	init = tf.global_variables_initializer()

	# --- Training Loop ---------------------------------------------------------------


	config = tf.ConfigProto()
	#config.gpu_options.per_process_gpu_memory_fraction = 0.2
	config.log_device_placement = False
	config.allow_soft_placement = False
	with tf.Session(config=config) as sess:

		# --- Create data --------------------

		ind = list(range(784))
		shuffle(ind)

		mnist = input_data.read_data_sets("/tmp/data/", one_hot=False)

		sess.run(init)

		step = 0


		while step < FLAGS.iter:

			batch_x, batch_y = mnist_data(mnist, FLAGS.batch_size, ind, "train")

			loss, acc = sess.run([cost, accuracy], feed_dict={x:batch_x,y:batch_y})

			sess.run(optimizer, feed_dict={x: batch_x, y: batch_y})
			print(" Iter: " + str(step) + ", Minibatch Loss= " + \
			  "{:.6f}".format(loss) + ", Training Accuracy= " + \
			  "{:.5f}".format(acc))


			if step % 500 == 499:
				val_x, val_y = mnist_data(mnist, n_val, ind, "validation")
				val_index = 0
				val_acc_list = []
				val_loss_list = []
				for i in range(50):
					batch_x = val_x[val_index: val_index + 100]
					batch_y = val_y[val_index: val_index + 100]
					val_index += 100
					val_acc_list.append(sess.run(accuracy, feed_dict={x: batch_x, y: batch_y}))
					val_loss_list.append(sess.run(cost, feed_dict={x: batch_x, y: batch_y}))
				val_acc = np.mean(val_acc_list)
				val_loss = np.mean(val_loss_list)
				print("Iter " + str(step) + ", Validation Loss= " + \
				  "{:.6f}".format(val_loss) + ", Validation Accuracy= " + \
				  "{:.5f}".format(val_acc))

			step += 1

			
				

		print("Optimization Finished!")

		
		# --- test ----------------------

		test_x, test_y = mnist_data(mnist, n_test, ind, "test")
		test_index = 0
		test_acc_list = []
		test_loss_list = []

		for i in range(100):
			batch_x = test_x[test_index: test_index + 100]
			batch_y = test_y[test_index: test_index + 100]

			test_index += 100
			test_acc_list.append(sess.run(accuracy, feed_dict={x: batch_x, y: batch_y}))
			test_loss_list.append(sess.run(cost, feed_dict={x: batch_x, y: batch_y}))

		test_acc = np.mean(test_acc_list)
		test_loss = np.mean(test_loss_list)

		print("Test result: Loss= " + "{:.6f}".format(test_loss) + ", Accuracy= " + "{:.5f}".format(test_acc))


				



if __name__=="__main__":
    tf.app.run()

