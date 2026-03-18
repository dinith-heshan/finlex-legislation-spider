import argparse
import sys

print(sys.argv)

parser = argparse.ArgumentParser(description="Train ML model")

parser.add_argument("--input", required=True)
parser.add_argument("--epochs", type=int, default=10)
parser.add_argument("--lr", type=float, default=0.001)
parser.add_argument("--use-gpu", action="store_true")

args = parser.parse_args()

print(args)

# python tests/argparse-module-test/test-1.py --input data.csv --epochs 20 --use-gpu