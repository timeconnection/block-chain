import requests
import json
from flask import Flask, request
from bitcoin_project.src.node import Block, Blockchain


app = Flask(__name__)

blockchain = Blockchain()


@app.route('/new_transaction', methods=['POST'])
def new_transaction():

    tx_data = request.get_json()

    required_fields = ["author", "content"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    blockchain.add_new_transaction(tx_data)
    return "success", 201


@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data), "chain":chain_data})


@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    return "Block {} is mined".format(result)


@app.route('/pending_tx', methods=['GET'])
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


# and now , we have a block chain can run in one compute, but we need a peer to peer block chain.how to understand this.
peers = set()


@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    peers.add(node_address)

    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    node_address = request.get_json()['node_address']
    if not node_address:
        return "Invalid data", 400

    data = {"node_address":request.host_url}
    headers = {"Content-Type": "application/json"}

    response = requests.post(node_address + "/register_node",
                            data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers

        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registeraion successful", 200
    else:
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):

    blockchain = Blockchain()

    for idx, block_data in enumerate(chain_dump):
        block = Block(block_data['index'],
                      block_data['transactions'],
                      block_data['timestamp'],
                      block_data['previous_hash'])
        proof = block_data['hash']

        if idx > 0:
            added = blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
        else:
            blockchain.chain.append(block)
    return blockchain


@app.route('/add_block', method=['POST'])
def verify_add_block():
    block_data = request.get_json()
    block = Block(block_data['index'],
                  block_data['transactions'],
                  block_data['timestamp'],
                  block_data['previous_hash'])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)
    if not added:
        return "The block was discarded by the node", 400

    return "Block added to chain", 201


@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transaction():
    result = blockchain.mine()
    if not result:
        return "No transaction to mine"
    else:
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            announce_new_blcok(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)


def announce_new_blcok(block):
    for peer in peers:
        url = "{}add_block".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))



def consensus():
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get("{}/chain".format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True
    return False










