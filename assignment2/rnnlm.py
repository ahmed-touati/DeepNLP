from numpy import *
import itertools
import time
import sys

# Import NN utils
from nn.base import NNBase
from nn.math import softmax, sigmoid
from nn.math import MultinomialSampler, multinomial_sample
from misc import random_weight_matrix


class RNNLM(NNBase):
    """
    Implements an RNN language model of the form:
    h(t) = sigmoid(H * h(t-1) + L[x(t)])
    y(t) = softmax(U * h(t))
    where y(t) predicts the next word in the sequence

    U = |V| * dim(h) as output vectors
    L = |V| * dim(h) as input vectors

    You should initialize each U[i,j] and L[i,j]
    as Gaussian noise with mean 0 and variance 0.1

    Arguments:
        L0 : initial input word vectors
        U0 : initial output word vectors
        alpha : default learning rate
        bptt : number of backprop timesteps
    """

    def __init__(self, L0, U0=None,
                 alpha=0.005, rseed=10, bptt=1):

        self.hdim = L0.shape[1] # word vector dimensions
        self.vdim = L0.shape[0] # vocab size
        param_dims = dict(H = (self.hdim, self.hdim),
                          U = L0.shape)
        # note that only L gets sparse updates
        param_dims_sparse = dict(L = L0.shape)
        NNBase.__init__(self, param_dims, param_dims_sparse)

        #### YOUR CODE HERE ####


        # Initialize word vectors
        # either copy the passed L0 and U0 (and initialize in your notebook)
        # or initialize with gaussian noise here
        self.sparams.L = 0.1 * random.standard_normal(self.sparams.L.shape)
        self.sparams.U = 0.1 * random.standard_normal(self.params.U.shape)

        # Initialize H matrix, as with W and U in part 1
        self.params.H = random_weight_matrix(*self.params.H.shape)
        self.bptt = bptt
        self.alpha = alpha
        #### END YOUR CODE ####


    def _acc_grads(self, xs, ys):
        """
        Accumulate gradients, given a pair of training sequences:
        xs = [<indices>] # input words
        ys = [<indices>] # output words (to predict)

        Your code should update self.grads and self.sgrads,
        in order for gradient_check and training to work.

        So, for example:
        self.grads.H += (your gradient dJ/dH)
        self.sgrads.L[i] = (gradient dJ/dL[i]) # update row

        Per the handout, you should:
            - make predictions by running forward in time
                through the entire input sequence
            - for *each* output word in ys, compute the
                gradients with respect to the cross-entropy
                loss for that output word
            - run backpropagation-through-time for self.bptt
                timesteps, storing grads in self.grads (for H, U)
                and self.sgrads (for L)

        You'll want to store your predictions \hat{y}(t)
        and the hidden layer values h(t) as you run forward,
        so that you can access them during backpropagation.

        At time 0, you should initialize the hidden layer to
        be a vector of zeros.
        """

        # Expect xs as list of indices
        ns = len(xs)

        # make matrix here of corresponding h(t)
        # hs[-1] = initial hidden state (zeros)
        hs = zeros((ns+1, self.hdim))
        # predicted probas
        ps = zeros((ns, self.vdim))

        #### YOUR CODE HERE ####

        ##
        # Forward propagation
        for t in range(0, ns):
            hs[t] = sigmoid(dot(self.params.H, hs[t-1]) + self.sparams.L[xs[t], :])
            ps[t] = softmax(dot(self.params.U, hs[t]))

        ##
        # Backward propagation through time
        dJdU = zeros(self.params.U.shape)
        dJdH = zeros(self.params.H.shape)


        delta_output = ps.copy() # (ns, vdim)
        delta_output[arange(0, ns), ys] -= 1
        for t in range(ns-1, -1, -1):
            Jt = -log(ps[t, ys[t]])

            dJdU += outer(delta_output[t], hs[t]) # (vdim, 1) * (1, hdim) = (vdim, hdim)

            # update delta
            delta = (self.params.U.T.dot(delta_output[t])) * hs[t] * (1-hs[t]) # (hdim, vdim) * (vdim, 1) = (hdim, 1)

            for step in range(t, max(0, t-self.bptt)-1, -1):
                dJdH += outer(delta, hs[step-1]) # (hdim, 1)* (1, hdim) = (hdim, hdim)
                self.sgrads.L[xs[step]] = delta
                # update delta
                delta = dot(self.params.H.T, delta) * hs[step] * (1-hs[step])

        self.grads.U = dJdU
        self.grads.H = dJdH




        #### END YOUR CODE ####



    def grad_check(self, x, y, outfd=sys.stderr, **kwargs):
        """
        Wrapper for gradient check on RNNs;
        ensures that backprop-through-time is run to completion,
        computing the full gradient for the loss as summed over
        the input sequence and predictions.

        Do not modify this function!
        """
        bptt_old = self.bptt
        self.bptt = len(y)
        print >> outfd, "NOTE: temporarily setting self.bptt = len(y) = %d to compute true gradient." % self.bptt
        NNBase.grad_check(self, x, y, outfd=outfd, **kwargs)
        self.bptt = bptt_old
        print >> outfd, "Reset self.bptt = %d" % self.bptt


    def compute_seq_loss(self, xs, ys):
        """
        Compute the total cross-entropy loss
        for an input sequence xs and output
        sequence (labels) ys.

        You should run the RNN forward,
        compute cross-entropy loss at each timestep,
        and return the sum of the point losses.
        """

        #J = 0
        ns = len(xs)
        #### YOUR CODE HERE ####
        # forward propagation
        hs = zeros((ns+1, self.hdim))
        ps = zeros((ns, self.vdim)) # predicted probas
        for t in range(0, ns):
            hs[t] = sigmoid(dot(self.params.H, hs[t-1]) + self.sparams.L[xs[t], :])
            ps[t] = softmax(dot(self.params.U, hs[t]))

        J = - sum(log(ps[arange(ns), ys]))

        #### END YOUR CODE ####
        return J


    def compute_loss(self, X, Y):
        """
        Compute total loss over a dataset.
        (wrapper for compute_seq_loss)

        Do not modify this function!
        """
        if not isinstance(X[0], ndarray): # single example
            return self.compute_seq_loss(X, Y)
        else: # multiple examples
            return sum([self.compute_seq_loss(xs,ys)
                       for xs,ys in itertools.izip(X, Y)])

    def compute_mean_loss(self, X, Y):
        """
        Normalize loss by total number of points.

        Do not modify this function!
        """
        J = self.compute_loss(X, Y)
        ntot = sum(map(len,Y))
        return J / float(ntot)


    def generate_sequence(self, init, end, maxlen=100):
        """
        Generate a sequence from the language model,
        by running the RNN forward and selecting,
        at each timestep, a random word from the
        a word from the emitted probability distribution.

        The MultinomialSampler class (in nn.math) may be helpful
        here for sampling a word. Use as:

            y = multinomial_sample(p)

        to sample an index y from the vector of probabilities p.


        Arguments:
            init = index of start word (word_to_num['<s>'])
            end = index of end word (word_to_num['</s>'])
            maxlen = maximum length to generate

        Returns:
            ys = sequence of indices
            J = total cross-entropy loss of generated sequence
        """

        J = 0 # total loss
        ys = [init] # emitted sequence
        ht = zeros(self.hdim)

        #### YOUR CODE HERE ####
        for t in range(maxlen):
            if ys[-1] == end:
                break
            ht = sigmoid(dot(self.params.H, ht) + self.sparams.L[ys[t], :])
            pt = softmax(dot(self.params.U, ht))
            yt = multinomial_sample(pt)
            ys.append(yt)
            J -= log(pt[yt])

        #### YOUR CODE HERE ####
        return ys, J



class ExtraCreditRNNLM(RNNLM):
    """
    Implements an improved RNN language model,
    for better speed and/or performance.

    We're not going to place any constraints on you
    for this part, but we do recommend that you still
    use the starter code (NNBase) framework that
    you've been using for the NER and RNNLM models.
    """

    def __init__(self, *args, **kwargs):
        #### YOUR CODE HERE ####
        raise NotImplementedError("__init__() not yet implemented.")
        #### END YOUR CODE ####

    def _acc_grads(self, xs, ys):
        #### YOUR CODE HERE ####
        raise NotImplementedError("_acc_grads() not yet implemented.")
        #### END YOUR CODE ####

    def compute_seq_loss(self, xs, ys):
        #### YOUR CODE HERE ####
        raise NotImplementedError("compute_seq_loss() not yet implemented.")
        #### END YOUR CODE ####

    def generate_sequence(self, init, end, maxlen=100):
        #### YOUR CODE HERE ####
        raise NotImplementedError("generate_sequence() not yet implemented.")
        #### END YOUR CODE ####