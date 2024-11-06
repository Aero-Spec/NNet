import sys
import onnx
import numpy as np
from onnx import helper, numpy_helper, TensorProto
from NNet.utils.readNNet import readNNet
from NNet.utils.normalizeNNet import normalizeNNet
import argparse
from typing import Optional

def nnet2onnx(
    nnetFile: str, 
    onnxFile: Optional[str] = "", 
    outputVar: str = "y_out", 
    inputVar: str = "X", 
    normalizeNetwork: bool = False
) -> None:
    """
    Convert a .nnet file to ONNX format.

    Args:
        nnetFile (str): Path to the .nnet file to convert.
        onnxFile (Optional[str]): Optional, name for the created .onnx file. Defaults to the same name as the .nnet file.
        outputVar (str): Optional, name of the output variable in ONNX. Defaults to 'y_out'.
        inputVar (str): Name of the input variable in ONNX. Defaults to 'X'.
        normalizeNetwork (bool): If True, adapt the network weights and biases so that networks and inputs 
                                 do not need normalization. Defaults to False.
    """
    try:
        if normalizeNetwork:
            weights, biases = normalizeNNet(nnetFile)
        else:
            weights, biases = readNNet(nnetFile)
    except FileNotFoundError as e:
        print(f"Error: The file {nnetFile} was not found.")
        raise e  # Raising the exception instead of exiting
    
    inputSize = weights[0].shape[1]
    outputSize = weights[-1].shape[0]
    numLayers = len(weights)

    # Default ONNX filename if none specified
    if not onnxFile:
        onnxFile = f"{nnetFile[:-5]}.onnx"

    # Initialize the graph
    inputs = [helper.make_tensor_value_info(inputVar, TensorProto.FLOAT, [inputSize])]
    outputs = [helper.make_tensor_value_info(outputVar, TensorProto.FLOAT, [outputSize])]
    operations = []
    initializers = []

    # Build the ONNX model layer by layer
    for i in range(numLayers):
        weight_name = f"W{i}"
        bias_name = f"B{i}"
        matmul_output = f"M{i}"
        add_output = f"H{i}"

        # Use the final output variable name for the last layer
        if i == numLayers - 1:
            add_output = outputVar

        # Add weight matrix multiplication
        operations.append(helper.make_node("MatMul", [inputVar, weight_name], [matmul_output]))
        initializers.append(numpy_helper.from_array(weights[i].astype(np.float32), name=weight_name))

        # Add bias addition
        operations.append(helper.make_node("Add", [matmul_output, bias_name], [add_output]))
        initializers.append(numpy_helper.from_array(biases[i].astype(np.float32), name=bias_name))

        # Apply ReLU activation to all layers except the last
        if i < numLayers - 1:
            relu_output = f"R{i}"
            operations.append(helper.make_node("Relu", [add_output], [relu_output]))
            inputVar = relu_output
        else:
            inputVar = add_output  # Update inputVar to use as input for the next layer

    # Create the graph and model in ONNX format
    graph_proto = helper.make_graph(operations, "nnet2onnx_Model", inputs, outputs, initializers)
    model_def = helper.make_model(graph_proto)

    # Print success message
    print(f"Converted NNet model at {nnetFile} to an ONNX model at {onnxFile}")

    # Save the ONNX model to file
    onnx.save(model_def, onnxFile)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Convert a .nnet file to ONNX format.")
    parser.add_argument("nnetFile", type=str, help="The .nnet file to convert")
    parser.add_argument("--onnxFile", type=str, default="", help="Optional: Name of the output ONNX file")
    parser.add_argument("--outputVar", type=str, default="y_out", help="Optional: Name of the output variable")
    parser.add_argument("--inputVar", type=str, default="X", help="Optional: Name of the input variable")
    parser.add_argument("--normalize", action="store_true", help="Normalize network weights and biases")

    args = parser.parse_args()

    # Call the nnet2onnx function with parsed arguments
    nnet2onnx(
        nnetFile=args.nnetFile, 
        onnxFile=args.onnxFile, 
        outputVar=args.outputVar, 
        inputVar=args.inputVar, 
        normalizeNetwork=args.normalize
    )

if __name__ == "__main__":
    main()
