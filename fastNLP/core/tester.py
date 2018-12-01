import itertools
from collections import defaultdict

import torch

from fastNLP.core.batch import Batch
from fastNLP.core.sampler import RandomSampler
from fastNLP.core.utils import _build_args
from fastNLP.core.utils import get_func_signature

class Tester(object):
    """An collection of model inference and evaluation of performance, used over validation/dev set and test set. """

    def __init__(self, data, model, metrics, batch_size=16, use_cuda=False, verbose=0):
        super(Tester, self).__init__()
        self.use_cuda = use_cuda
        self.data = data
        self.batch_size = batch_size
        self.verbose = verbose
        if torch.cuda.is_available() and self.use_cuda:
            self._model = model.cuda()
        else:
            self._model = model
        if hasattr(self._model, 'predict'):
            if not callable(self._model.predict):
                raise TypeError(f"{get_func_signature(model.predict)} must be callable to be used "
                                f"for evaluation.")
            self._predict_func = self._model.predict
        else:
            self._predict_func = self._model


    def test(self):
        # turn on the testing mode; clean up the history
        network = self._model
        self.mode(network, is_test=True)
        output, truths = defaultdict(list), defaultdict(list)
        data_iterator = Batch(self.data, self.batch_size, sampler=RandomSampler(), as_numpy=False)

        with torch.no_grad():
            for batch_x, batch_y in data_iterator:
                prediction = self.data_forward(network, batch_x)
                assert isinstance(prediction, dict)
                for k, v in prediction.items():
                    output[k].append(v)
                for k, v in batch_y.items():
                    truths[k].append(v)
            for k, v in output.items():
                output[k] = itertools.chain(*v)
            for k, v in truths.items():
                truths[k] = itertools.chain(*v)
            # args = _build_args(self._evaluator, **output, **truths)
            eval_results = self._evaluator(**args)
        if self.verbose >= 0:
            print("[tester] {}".format(self.print_eval_results(eval_results)))
        self.mode(network, is_test=False)
        return eval_results

    def mode(self, model, is_test=False):
        """Train mode or Test mode. This is for PyTorch currently.

        :param model: a PyTorch model
        :param is_test: bool, whether in test mode or not.

        """
        if is_test:
            model.eval()
        else:
            model.train()

    def data_forward(self, network, x):
        """A forward pass of the model. """
        x = _build_args(network.forward, **x)
        y = self._predict_func(**x)
        return y

    def print_eval_results(self, results):
        """Override this method to support more print formats.

        :param results: dict, (str: float) is (metrics name: value)

        """
        return ", ".join([str(key) + "=" + str(value) for key, value in results.items()])
