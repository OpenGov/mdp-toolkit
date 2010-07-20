
import unittest
import numpy as n

import mdp

from bimdp import BiFlow, MSG_ID_SEP
from bimdp.hinet import BiFlowNode, CloneBiLayer, BiSwitchboard
from bimdp.nodes import SFABiNode, IdentityBiNode


class TestBiFlowNode(unittest.TestCase):
    """Test the behavior of the BiFlowNode."""

    def test_two_nodes1(self):
        """Test a TestBiFlowNode with two normal nodes."""
        sfa_node = mdp.nodes.SFANode(input_dim=10, output_dim=8)
        sfa2_node = mdp.nodes.SFA2Node(input_dim=8, output_dim=6)
        flownode = BiFlowNode(BiFlow([sfa_node, sfa2_node]))
        for _ in range(2):
            for _ in range(6):
                flownode.train(n.random.random((30,10)))
            flownode.stop_training()
        x = n.random.random([100,10])
        flownode.execute(x)

    def test_two_nodes2(self):
        """Test a TestBiFlowNode with two normal nodes using a normal Flow."""
        sfa_node = mdp.nodes.SFANode(input_dim=10, output_dim=8)
        sfa2_node = mdp.nodes.SFA2Node(input_dim=8, output_dim=6)
        flownode = BiFlowNode(BiFlow([sfa_node, sfa2_node]))
        flow = mdp.Flow([flownode])
        data_iterables = [[n.random.random((30,10)) for _ in range(6)]]
        flow.train(data_iterables)
        x = n.random.random([100,10])
        flow.execute(x)

    def test_pretrained_nodes(self):
        """Test a TestBiFlowNode with two normal pretrained nodes."""
        sfa_node = mdp.nodes.SFANode(input_dim=10, output_dim=8)
        sfa2_node = mdp.nodes.SFA2Node(input_dim=8, output_dim=6)
        flownode = BiFlowNode(BiFlow([sfa_node, sfa2_node]))
        flow = mdp.Flow([flownode])
        data_iterables = [[n.random.random((30,10)) for _ in range(6)]]
        flow.train(data_iterables)
        pretrained_flow = flow[0]._flow
        biflownode = BiFlowNode(pretrained_flow)
        x = n.random.random([100,10])
        biflownode.execute(x)


class DummyBiNode(IdentityBiNode):
    """Dummy class for CloneBiLayer tests."""

    def _execute(self, x, data1, data2):
        self.data1 = data1
        self.data2 = data2
        return x

    def is_trainable(self):
        return False


class TestCloneBiLayer(unittest.TestCase):
    """Test the behavior of the BiCloneLayer."""

    def test_clonelayer(self):
        """Test a simple clonelayer with three SFA Nodes."""
        sfa_node = SFABiNode(input_dim=3, output_dim=2)
        clonelayer = CloneBiLayer(sfa_node, 3)
        x = n.random.random((100,9))
        clonelayer.train(x)
        clonelayer.stop_training()
        clonelayer.execute(x)

    def test_use_copies_msg(self):
        """Test the correct reaction to an outgoing use_copies message."""
        stop_result = ({"clonelayer" + MSG_ID_SEP + "use_copies": True}, 1)
        stop_sfa_node = SFABiNode(stop_result=stop_result,
                                  input_dim=10, output_dim=3)
        clonelayer = CloneBiLayer(node=stop_sfa_node,
                                  n_nodes=3,
                                  use_copies=False,
                                  node_id="clonelayer")
        x = n.random.random((100,30))
        clonelayer.train(x)
        clonelayer.stop_training()
        assert(clonelayer.use_copies is True)

    def test_use_copies_msg_flownode(self):
        """Test the correct reaction to an outgoing use_copies message."""
        stop_result = ({"clonelayer" + MSG_ID_SEP + "use_copies": True},
                       "clonelayer")
        stop_sfa_node = SFABiNode(stop_result=stop_result,
                                  input_dim=10, output_dim=3)
        biflownode = BiFlowNode(BiFlow([stop_sfa_node]))
        clonelayer = CloneBiLayer(node=biflownode,
                                  n_nodes=3,
                                  use_copies=False,
                                  node_id="clonelayer")
        x = n.random.random((100,30))
        clonelayer.train(x)
        clonelayer.stop_training()
        assert(clonelayer.use_copies is True)

    def test_message_splitting(self):
        """Test message array splitting and combination."""
        node = DummyBiNode(input_dim=3)
        clonelayer = CloneBiLayer(node, 2, use_copies=True)
        x = n.random.random((10, 6))
        data1 = n.random.random((10, 4))  # should be split
        data2 = n.random.random((10, 5))  # should not be touched
        msg = {
            "string": "blabla",
            "list": [1,2],
            "data1": data1,
            "data2": data2,
        }
        y, out_msg = clonelayer.execute(x, msg)
        node1, node2 = clonelayer.nodes
        self.assertTrue(n.all(x == y))
        self.assertTrue(out_msg["string"] == msg["string"])
        self.assertTrue(out_msg["list"] == msg["list"])
        self.assertTrue(n.all(out_msg["data1"] == data1))
        self.assertTrue(n.all(node1.data1 == data1[:,:2]))
        self.assertTrue(n.all(node2.data1 == data1[:,2:]))
        self.assertTrue(out_msg["data2"] is data2)
        self.assertTrue(n.all(node1.data2 is data2))
        self.assertTrue(n.all(node2.data2 is data2))


class TestBiSwitchboardNode(unittest.TestCase):
    """Test the behavior of the BiSwitchboardNode."""

    def test_execute_routing(self):
        """Test the standard routing for messages."""
        sboard = BiSwitchboard(input_dim=3, connections=[2,0,1])
        x = n.array([[1,2,3],[4,5,6]])
        msg = {
            "string": "blabla",
            "list": [1,2],
            "data": x.copy(),  # should be mapped by switchboard
            "data2": n.zeros(3),  # should not be modified
            "data3": n.zeros((3,4)),  # should not be modified
        }
        y, out_msg = sboard.execute(x, msg)
        reference_y = n.array([[3,1,2],[6,4,5]])
        self.assertTrue(n.all(y == reference_y))
        self.assertTrue(out_msg["string"] == msg["string"])
        self.assertTrue(out_msg["list"] == msg["list"])
        self.assertTrue(n.all(out_msg["data"] == reference_y))
        self.assertTrue(out_msg["data2"].shape == (3,))
        self.assertTrue(out_msg["data3"].shape == (3,4))

    def test_inverse_message_routing(self):
        """Test the inverse routing for messages."""
        sboard = BiSwitchboard(input_dim=3, connections=[2,0,1])
        x = n.array([[1,2,3],[4,5,6]])
        msg = {
            "string": "blabla",
            "method": "inverse",
            "list": [1,2],
            "data": x,  # should be mapped by switchboard
            "data2": n.zeros(3),  # should not be modified
            "data3": n.zeros((3,4)),  # should not be modified
            "target": "test"
        }
        y, out_msg, target = sboard.execute(None, msg)
        self.assertTrue(y is None)
        self.assertTrue(target == "test")
        reference_y = n.array([[2,3,1],[5,6,4]])
        self.assertTrue(out_msg["string"] == msg["string"])
        self.assertTrue(out_msg["list"] == msg["list"])
        self.assertTrue(n.all(out_msg["data"] == reference_y))
        self.assertTrue(out_msg["data2"].shape == (3,))
        self.assertTrue(out_msg["data3"].shape == (3,4))

    def test_stop_message(self):
        """Test the inverse routing for messages."""
        sboard = BiSwitchboard(input_dim=3, connections=[2,0,1])
        x = n.array([[1,2,3],[4,5,6]])
        msg = {
            "string": "blabla",
            "list": [1,2],
            "data": x,  # should be mapped by switchboard
            "data2": n.zeros(3),  # should not be modified
            "data3": n.zeros((3,4)),  # should not be modified
            "target": "node123"
        }
        out_msg, _ = sboard.stop_message(msg)
        reference_y = n.array([[3,1,2],[6,4,5]])
        self.assertTrue(n.all(out_msg["data"] == reference_y))
        self.assertTrue(out_msg["string"] == msg["string"])
        self.assertTrue(out_msg["list"] == msg["list"])
        self.assertTrue(n.all(out_msg["data"] == reference_y))
        self.assertTrue(out_msg["data2"].shape == (3,))
        self.assertTrue(out_msg["data3"].shape == (3,4))


def get_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBiFlowNode))
    suite.addTest(unittest.makeSuite(TestCloneBiLayer))
    suite.addTest(unittest.makeSuite(TestBiSwitchboardNode))
    return suite

if __name__ == '__main__':
    unittest.main()
