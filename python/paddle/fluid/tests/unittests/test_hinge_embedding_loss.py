# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import paddle
import paddle.fluid as fluid
import numpy as np
import unittest

np.random.seed(42)


class TestFunctionalHingeEmbeddingLoss(unittest.TestCase):
    def setUp(self):
        self.delta = 1.0
        self.shape = (10, 10, 5)
        self.input_np = np.random.random(size=self.shape).astype(np.float32)
        self.label_np_1 = np.ones(shape=self.input_np.shape).astype(
            np.float32)  # 1.
        self.label_np_2 = 0. - np.ones(shape=self.input_np.shape).astype(
            np.float32)  # -1.
        self.wrong_label = paddle.zeros(shape=self.shape).astype(
            paddle.float32)  # not 1. and not -1.

    def run_dynamic_label_1(self):
        """
        when label is full of 1.
        """
        input = paddle.to_tensor(self.input_np)
        label = paddle.to_tensor(self.label_np_1)
        dy_result = paddle.nn.functional.hinge_embedding_loss(input, label)
        expected = np.mean(self.input_np)
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        dy_result = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='sum')
        expected = np.sum(self.input_np)
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        dy_result = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='none')
        expected = self.input_np
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, self.shape)

    def run_dynamic_label_2(self):
        """
        when label is full of -1.
        """
        input = paddle.to_tensor(self.input_np)
        label = paddle.to_tensor(self.label_np_2)
        dy_result = paddle.nn.functional.hinge_embedding_loss(input, label)
        expected = np.mean(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        dy_result = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='sum')
        expected = np.sum(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        dy_result = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='none')
        expected = np.maximum(0., self.delta - self.input_np)
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, self.shape)

    def run_static_label_1(self, use_gpu=False):
        input = paddle.fluid.data(
            name='input', shape=self.shape, dtype='float32')
        label = paddle.fluid.data(
            name='label', shape=self.shape, dtype='float32')
        result0 = paddle.nn.functional.hinge_embedding_loss(input, label)
        result1 = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='sum')
        result2 = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='none')
        y = paddle.nn.functional.hinge_embedding_loss(input, label, name='aaa')

        place = fluid.CUDAPlace(0) if use_gpu else fluid.CPUPlace()
        exe = fluid.Executor(place)
        exe.run(fluid.default_startup_program())
        static_result = exe.run(
            feed={"input": self.input_np,
                  "label": self.label_np_1},
            fetch_list=[result0, result1, result2])

        expected = np.mean(self.input_np)
        self.assertTrue(np.allclose(static_result[0], expected))
        expected = np.sum(self.input_np)
        self.assertTrue(np.allclose(static_result[1], expected))
        expected = self.input_np
        self.assertTrue(np.allclose(static_result[2], expected))

        self.assertTrue('aaa' in y.name)

    def run_static_label_2(self, use_gpu=False):
        input = paddle.fluid.data(
            name='input', shape=self.shape, dtype='float32')
        label = paddle.fluid.data(
            name='label', shape=self.shape, dtype='float32')
        result0 = paddle.nn.functional.hinge_embedding_loss(
            input, label, name="label 2, mean")
        result1 = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='sum')
        result2 = paddle.nn.functional.hinge_embedding_loss(
            input, label, reduction='none')
        y = paddle.nn.functional.hinge_embedding_loss(input, label, name='aaa')

        place = fluid.CUDAPlace(0) if use_gpu else fluid.CPUPlace()
        exe = fluid.Executor(place)
        exe.run(fluid.default_startup_program())
        static_result = exe.run(
            feed={"input": self.input_np,
                  "label": self.label_np_1},
            fetch_list=[result0, result1, result2])

        expected = np.mean(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(static_result[0], expected))
        expected = np.sum(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(static_result[1], expected))
        expected = np.maximum(0., self.delta - self.input_np)
        self.assertTrue(np.allclose(static_result[2], expected))

        self.assertTrue('aaa' in y.name)

    def test_cpu(self):
        paddle.disable_static(place=paddle.fluid.CPUPlace())
        self.run_dynamic_label_1()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_1()

        paddle.disable_static(place=paddle.fluid.CPUPlace())
        self.run_dynamic_label_2()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_2()

    def test_gpu(self):
        if not fluid.core.is_compiled_with_cuda():
            return

        paddle.disable_static(place=paddle.fluid.CUDAPlace(0))
        self.run_dynamic_label_1()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_1(use_gpu=True)

        paddle.disable_static(place=paddle.fluid.CUDAPlace(0))
        self.run_dynamic_label_2()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_2(use_gpu=True)

    # test case the raise message
    def test_reduce_errors(self):
        def test_value_error():
            loss = paddle.nn.functional.hinge_embedding_loss(
                self.input_np, self.label_np_1, reduction='reduce_mean')

        self.assertRaises(ValueError, test_value_error)

    def test_label_errors(self):
        paddle.disable_static()

        def test_value_error():
            loss = paddle.nn.functional.hinge_embedding_loss(
                paddle.to_tensor(self.input_np), self.wrong_label)

        self.assertRaises(ValueError, test_value_error)


class TestClassHingeEmbeddingLoss(unittest.TestCase):
    def setUp(self):
        self.delta = 1.0
        self.shape = (10, 10, 5)
        self.input_np = np.random.random(size=self.shape).astype(np.float32)
        self.label_np_1 = np.ones(shape=self.input_np.shape).astype(
            np.float32)  # 1.
        self.label_np_2 = 0. - np.ones(shape=self.input_np.shape).astype(
            np.float32)  # -1.
        self.wrong_label = paddle.zeros(shape=self.shape).astype(
            paddle.float32)  # not 1. and not -1.

    def run_dynamic_label_1(self):
        """
        when label is full of 1.
        """
        input = paddle.to_tensor(self.input_np)
        label = paddle.to_tensor(self.label_np_1)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss()
        dy_result = hinge_embedding_loss(input, label)
        expected = np.mean(self.input_np)
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='sum')
        dy_result = hinge_embedding_loss(input, label)
        expected = np.sum(self.input_np)
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='none')
        dy_result = hinge_embedding_loss(input, label)
        expected = self.input_np
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, self.shape)

    def run_dynamic_label_2(self):
        """
        when label is full of -1.
        """
        input = paddle.to_tensor(self.input_np)
        label = paddle.to_tensor(self.label_np_2)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss()
        dy_result = hinge_embedding_loss(input, label)
        expected = np.mean(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='sum')
        dy_result = hinge_embedding_loss(input, label)
        expected = np.sum(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, [1])

        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='none')
        dy_result = hinge_embedding_loss(input, label)
        expected = np.maximum(0., self.delta - self.input_np)
        self.assertTrue(np.allclose(dy_result.numpy(), expected))
        self.assertTrue(dy_result.shape, self.shape)

    def run_static_label_1(self, use_gpu=False):
        input = paddle.fluid.data(
            name='input', shape=self.shape, dtype='float32')
        label = paddle.fluid.data(
            name='label', shape=self.shape, dtype='float32')
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss()
        result0 = hinge_embedding_loss(input, label)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='sum')
        result1 = hinge_embedding_loss(input, label)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='none')
        result2 = hinge_embedding_loss(input, label)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(name='aaa')
        result3 = hinge_embedding_loss(input, label)

        place = fluid.CUDAPlace(0) if use_gpu else fluid.CPUPlace()
        exe = fluid.Executor(place)
        exe.run(fluid.default_startup_program())
        static_result = exe.run(
            feed={"input": self.input_np,
                  "label": self.label_np_1},
            fetch_list=[result0, result1, result2])

        expected = np.mean(self.input_np)
        self.assertTrue(np.allclose(static_result[0], expected))
        expected = np.sum(self.input_np)
        self.assertTrue(np.allclose(static_result[1], expected))
        expected = self.input_np
        self.assertTrue(np.allclose(static_result[2], expected))
        self.assertTrue('aaa' in result3.name)

    def run_static_label_2(self, use_gpu=False):
        input = paddle.fluid.data(
            name='input', shape=self.shape, dtype='float32')
        label = paddle.fluid.data(
            name='label', shape=self.shape, dtype='float32')
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss()
        result0 = hinge_embedding_loss(input, label)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='sum')
        result1 = hinge_embedding_loss(input, label)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
            reduction='none')
        result2 = hinge_embedding_loss(input, label)
        hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(name='aaa')
        result3 = hinge_embedding_loss(input, label)

        place = fluid.CUDAPlace(0) if use_gpu else fluid.CPUPlace()
        exe = fluid.Executor(place)
        exe.run(fluid.default_startup_program())
        static_result = exe.run(
            feed={"input": self.input_np,
                  "label": self.label_np_2},
            fetch_list=[result0, result1, result2])

        expected = np.mean(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(static_result[0], expected))
        expected = np.sum(np.maximum(0., self.delta - self.input_np))
        self.assertTrue(np.allclose(static_result[1], expected))
        expected = np.maximum(0., self.delta - self.input_np)
        self.assertTrue(np.allclose(static_result[2], expected))
        self.assertTrue('aaa' in result3.name)

    def test_cpu(self):
        paddle.disable_static(place=paddle.fluid.CPUPlace())
        self.run_dynamic_label_1()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_1()

        paddle.disable_static(place=paddle.fluid.CPUPlace())
        self.run_dynamic_label_2()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_2()

        paddle.disable_static(place=paddle.fluid.CPUPlace())

    def test_gpu(self):
        if not fluid.core.is_compiled_with_cuda():
            return

        paddle.disable_static(place=paddle.fluid.CUDAPlace(0))
        self.run_dynamic_label_1()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_1(use_gpu=True)

        paddle.disable_static(place=paddle.fluid.CUDAPlace(0))
        self.run_dynamic_label_2()
        paddle.enable_static()

        with fluid.program_guard(fluid.Program()):
            self.run_static_label_2(use_gpu=True)

        paddle.disable_static(place=paddle.fluid.CUDAPlace(0))

    # test case the raise message
    def test_reduce_errors(self):
        def test_value_error():
            hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss(
                reduction='reduce_mean')
            loss = hinge_embedding_loss(self.input_np, self.label_np_1)

        self.assertRaises(ValueError, test_value_error)

    def test_label_errors(self):
        paddle.disable_static()

        def test_value_error():
            hinge_embedding_loss = paddle.nn.loss.HingeEmbeddingLoss()
            loss = hinge_embedding_loss(
                paddle.to_tensor(self.input_np), self.wrong_label)

        self.assertRaises(ValueError, test_value_error)


if __name__ == "__main__":
    unittest.main()
