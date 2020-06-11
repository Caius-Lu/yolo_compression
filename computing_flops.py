import torch
import argparse
from thop import profile
from models import Darknet, SparseYOLO, SoftDarknet, YOLO_Nano
from utils.pruning import create_mask_LTH, apply_mask_LTH


parser = argparse.ArgumentParser()
parser.add_argument('--model', type=str, help='Path to load the model.', required=True)
parser.add_argument('--darknet', type=str, help='Architecture to create.', required=True)
parser.add_argument('--cfg', type=str, help='args file to create the model.')
parser.add_argument('--mask', type=str, default=None, help='Path to load the mask, if existis.')
parser.add_argument('--embbed', action='store_true', help='To load the mask from the same checkpoint of model.')
parser.add_argument('--device', help='cuda:id or cpu', required=True)
# parser.add_argument('--clever_format', action='store_true')
args = vars(parser.parse_args())

device = torch.device(args['device'])
x = torch.Tensor(1, 3, 416, 416).to(device)

# Initialize model
if args['darknet'] == 'default':
    model = Darknet(args['cfg']).to(device)
elif args['darknet'] == 'nano':
    model = YOLO_Nano().to(device)
elif args['darknet'] == 'soft':
    model = SoftDarknet(args['cfg']).to(device)
    model.ticket = True
    _ = model(x)


checkpoint = torch.load(args['model'], map_location=device)
try:
    model.load_state_dict(checkpoint['model'])
except:
    print("model key don't found in checkpoint. Trying without model key")
    model.load_state_dict(checkpoint)

if args['darknet'] != 'soft' and (args['mask'] or args['embbed']):
    mask = create_mask_LTH(model)
    if args['mask']: mask.load_state_dict(torch.load(args['mask'], map_location=device))
    else: mask.load_state_dict(checkpoint['mask'])
    apply_mask_LTH(model, mask)

if args['darknet'] == 'nano': total_ops, total_params = profile(model, (x,), verbose=True)
else:
    sparse = SparseYOLO(model).to(device)
    total_ops, total_params = profile(sparse, (x, ), verbose=True)

print("%s | %s" % ("Params(M)", "FLOPs(G)"))
print("---|---")
print("%.2f | %.2f" % (total_params / (1000 ** 2), total_ops / (1000 ** 3)))