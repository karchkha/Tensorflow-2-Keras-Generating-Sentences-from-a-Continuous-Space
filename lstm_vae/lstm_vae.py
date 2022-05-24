# coding: utf-8

# from tensorflow.keras import backend as K
import tensorflow as tf
# from tensorflow.keras import objectives
# from tensorflow.keras.layers import Input, LSTM
# from tensorflow.keras.layers.core import Dense, Lambda
# from tensorflow.keras.layers.wrappers import TimeDistributed
# from tensorflow.keras.models import Model


def create_lstm_vae(input_dim,
                    batch_size,  # we need it for sampling
                    intermediate_dim,
                    latent_dim):
    """
    Creates an LSTM Variational Autoencoder (VAE).

    # Arguments
        input_dim: int.
        batch_size: int.
        intermediate_dim: int, output shape of LSTM.
        latent_dim: int, latent z-layer shape.
        epsilon_std: float, z-layer sigma.


    # References
        - [Building Autoencoders in Keras](https://blog.keras.io/building-autoencoders-in-keras.html)
        - [Generating sentences from a continuous space](https://arxiv.org/abs/1511.06349)
    """
    x = tf.keras.Input(shape=(None, input_dim,), name="input1")

    # LSTM encoding
    h = tf.keras.layers.LSTM(units=intermediate_dim, name="lstm1")(x)

    # VAE Z layer
    z_mean = tf.keras.layers.Dense(units=latent_dim)(h)
    z_log_sigma = tf.keras.layers.Dense(units=latent_dim, name="dense1")(h)

    def sampling(args):
        z_mean, z_log_sigma = args
        epsilon = tf.random.normal(shape=(batch_size, latent_dim), mean=0., stddev=1.0)
        return z_mean + z_log_sigma * epsilon

    # note that "output_shape" isn't necessary with the TensorFlow backend
    # so you could write `Lambda(sampling)([z_mean, z_log_sigma])`
    z = tf.keras.layers.Lambda(sampling, output_shape=(latent_dim,), name="lambdaaaaaa")([z_mean, z_log_sigma])

    z_reweighting = tf.keras.layers.Dense(units=intermediate_dim, activation="linear")
    z_reweighted = z_reweighting(z)

    # "next-word" data for prediction
    decoder_words_input = tf.keras.Input(shape=(None, input_dim,), name="input2")

    # decoded LSTM layer
    decoder_h = tf.keras.layers.LSTM(intermediate_dim, return_sequences=True, return_state=True)

    # todo: not sure if this initialization is correct
    h_decoded, _, _ = decoder_h(decoder_words_input, initial_state=[z_reweighted, z_reweighted])
    decoder_dense = tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(input_dim, activation="softmax"))
    decoded_onehot = decoder_dense(h_decoded)

    # end-to-end autoencoder
    vae = tf.keras.Model([x, decoder_words_input], decoded_onehot)

    # encoder, from inputs to latent space
    encoder = tf.keras.Model(x, [z_mean, z_log_sigma])

    # generator, from latent space to reconstructed inputs -- for inference's first step
    decoder_state_input = tf.keras.Input(shape=(latent_dim,))
    _z_rewighted = z_reweighting(decoder_state_input)
    _h_decoded, _decoded_h, _decoded_c = decoder_h(decoder_words_input, initial_state=[_z_rewighted, _z_rewighted])
    _decoded_onehot = decoder_dense(_h_decoded)
    generator = tf.keras.Model([decoder_words_input, decoder_state_input], [_decoded_onehot, _decoded_h, _decoded_c])

    # RNN for inference
    input_h = tf.keras.Input(shape=(intermediate_dim,))
    input_c = tf.keras.Input(shape=(intermediate_dim,))
    __h_decoded, __decoded_h, __decoded_c = decoder_h(decoder_words_input, initial_state=[input_h, input_c])
    __decoded_onehot = decoder_dense(__h_decoded)
    stepper = tf.keras.Model([decoder_words_input, input_h, input_c], [__decoded_onehot, __decoded_h, __decoded_c])

    def vae_loss(x, x_decoded_onehot):
        
        z_mean_1, z_log_sigma_1 = encoder(x)


        xent_loss = tf.keras.metrics.categorical_crossentropy(x, x_decoded_onehot)

        kl_loss = - 0.5 * tf.keras.backend.mean(1 + z_log_sigma_1 - tf.keras.backend.square(z_mean_1) - tf.keras.backend.exp(z_log_sigma_1))
        
        
        # tf.keras.backend.mean(1 + z_log_sigma - tf.keras.backend.square(z_mean) - tf.keras.backend.exp(z_log_sigma))
        loss =  xent_loss + kl_loss 
        return loss

    vae.compile(optimizer="adam", loss=vae_loss)
    vae.summary()

    return vae, encoder, generator, stepper
