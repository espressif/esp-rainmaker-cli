# SPDX-FileCopyrightText: 2018-2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#

# APIs for interpreting and creating protobuf packets for
# protocomm endpoint with security type protocomm_security1

import base64
import hashlib
import sys
import os

# Import proto - it should be available from the parent module (rmaker_local_ctrl or rmaker_prov)
try:
    import proto
except ImportError:
    # Try to find proto in parent modules
    current_file = os.path.abspath(__file__)
    # Go up to rmaker_tools
    rmaker_tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    for parent in ['rmaker_prov', 'rmaker_local_ctrl']:
        parent_dir = os.path.join(rmaker_tools_dir, parent)
        proto_path = os.path.join(parent_dir, 'proto')
        if os.path.exists(proto_path):
            # Add parent directory to path so proto can be imported as a module
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            try:
                import proto
                break
            except ImportError:
                continue
    else:
        raise ImportError("Could not find proto module")

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    try:
        from ..utils.convenience import long_to_bytes, str_to_bytes
    except ImportError:
        def long_to_bytes(n: int) -> bytes:
            if n == 0:
                return b'\x00'
            return n.to_bytes((n.bit_length() + 7) // 8, 'big')
        
        def str_to_bytes(s):
            """Convert string to bytes"""
            if isinstance(s, str):
                return s.encode('latin-1')
            return s

    from .security import Security
except ImportError as err:
    raise err


def a_xor_b(a: bytes, b: bytes) -> bytes:
    return b''.join(long_to_bytes(a[i] ^ b[i]) for i in range(0, len(b)))


# Enum for state of protocomm_security1 FSM
class security_state:
    REQUEST1 = 0
    RESPONSE1_REQUEST2 = 1
    RESPONSE2 = 2
    FINISHED = 3


class Security1(Security):
    def __init__(self, pop, verbose):
        self.session_state = security_state.REQUEST1
        self.pop = str_to_bytes(pop)
        self.verbose = verbose
        self.ctr_offset = 0
        self.shared_key = None
        self.device_random = None
        Security.__init__(self, self.security1_session)

    def security1_session(self, response_data):
        # protocomm security1 FSM which interprets/forms
        # protobuf packets according to present state of session
        if (self.session_state == security_state.REQUEST1):
            self.session_state = security_state.RESPONSE1_REQUEST2
            return self.setup0_request()
        elif (self.session_state == security_state.RESPONSE1_REQUEST2):
            self.session_state = security_state.RESPONSE2
            self.setup0_response(response_data)
            return self.setup1_request()
        elif (self.session_state == security_state.RESPONSE2):
            self.session_state = security_state.FINISHED
            self.setup1_response(response_data)
            return None

        print('Unexpected state')
        return None

    def __generate_key(self):
        # Generate private and public key pair for client
        self.client_private_key = X25519PrivateKey.generate()
        self.client_public_key = self.client_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)

    def _print_verbose(self, data):
        if (self.verbose):
            print(f'\x1b[32;20m++++ {data} ++++\x1b[0m')

    def setup0_request(self):
        # Form SessionCmd0 request packet using client public key
        setup_req = proto.session_pb2.SessionData()
        setup_req.sec_ver = proto.session_pb2.SecScheme1
        self.__generate_key()
        setup_req.sec1.sc0.client_pubkey = self.client_public_key
        self._print_verbose(f'Client Public Key:\t0x{self.client_public_key.hex()}')
        return setup_req.SerializeToString().decode('latin-1')

    def setup0_response(self, response_data):
        # Interpret SessionResp0 response packet
        setup_resp = proto.session_pb2.SessionData()
        setup_resp.ParseFromString(str_to_bytes(response_data))
        self._print_verbose('Security version:\t' + str(setup_resp.sec_ver))
        if setup_resp.sec_ver != proto.session_pb2.SecScheme1:
            raise RuntimeError('Incorrect security scheme')

        self.device_public_key = setup_resp.sec1.sr0.device_pubkey
        # Device random is the initialization vector
        device_random = setup_resp.sec1.sr0.device_random
        self._print_verbose(f'Device Public Key:\t0x{self.device_public_key.hex()}')
        self._print_verbose(f'Device Random:\t0x{device_random.hex()}')

        # Calculate Curve25519 shared key using Client private key and Device public key
        sharedK = self.client_private_key.exchange(X25519PublicKey.from_public_bytes(self.device_public_key))
        self._print_verbose(f'Shared Key:\t0x{sharedK.hex()}')

        # If PoP is provided, XOR SHA256 of PoP with the previously
        # calculated Shared Key to form the actual Shared Key
        if len(self.pop) > 0:
            # Calculate SHA256 of PoP
            h = hashes.Hash(hashes.SHA256(), backend=default_backend())
            h.update(self.pop)
            digest = h.finalize()
            # XOR with and update Shared Key
            sharedK = a_xor_b(sharedK, digest)
            self._print_verbose(f'Updated Shared Key (Shared key XORed with PoP):\t0x{sharedK.hex()}')
        self.shared_key = sharedK
        self.device_random = bytes(device_random)
        cipher = Cipher(algorithms.AES(sharedK), modes.CTR(self.device_random), backend=default_backend())
        self.cipher = cipher.encryptor()

    def setup1_request(self):
        # Form SessionCmd1 request packet using encrypted device public key
        setup_req = proto.session_pb2.SessionData()
        setup_req.sec_ver = proto.session_pb2.SecScheme1
        setup_req.sec1.msg = proto.sec1_pb2.Session_Command1
        # Encrypt device public key and attach to the request packet
        client_verify = self.cipher.update(self.device_public_key)
        self.ctr_offset += len(self.device_public_key)
        self._print_verbose(f'Client Proof:\t0x{client_verify.hex()}')
        setup_req.sec1.sc1.client_verify_data = client_verify
        return setup_req.SerializeToString().decode('latin-1')

    def setup1_response(self, response_data):
        # Interpret SessionResp1 response packet
        setup_resp = proto.session_pb2.SessionData()
        setup_resp.ParseFromString(str_to_bytes(response_data))
        # Ensure security scheme matches
        if setup_resp.sec_ver == proto.session_pb2.SecScheme1:
            device_verify = setup_resp.sec1.sr1.device_verify_data
            self._print_verbose(f'Device Proof:\t0x{device_verify.hex()}')
            enc_client_pubkey = self.cipher.update(setup_resp.sec1.sr1.device_verify_data)
            self.ctr_offset += len(setup_resp.sec1.sr1.device_verify_data)
            if enc_client_pubkey != self.client_public_key:
                raise RuntimeError('Failed to verify device!')
        else:
            raise RuntimeError('Unsupported security protocol')

    def encrypt_data(self, data):
        result = self.cipher.update(data)
        self.ctr_offset += len(data)
        return result

    def decrypt_data(self, data):
        result = self.cipher.update(data)
        self.ctr_offset += len(data)
        return result

    def serialize(self):
        """
        Serialize session crypto state for disk persistence.
        Returns a dict suitable for JSON serialization.
        """
        if self.shared_key is None or self.device_random is None:
            return None
        pop_hash = ''
        if len(self.pop) > 0:
            pop_hash = hashlib.sha256(self.pop).hexdigest()
        return {
            'shared_key': base64.b64encode(self.shared_key).decode('ascii'),
            'device_random': base64.b64encode(self.device_random).decode('ascii'),
            'ctr_offset': self.ctr_offset,
            'pop_hash': pop_hash,
            'sec_ver': 1,
        }

    @classmethod
    def deserialize(cls, data, pop='', verbose=False):
        """
        Restore a Security1 object from serialized session data.
        Recreates the AES-CTR cipher and advances the counter to the saved offset.

        :param data: dict from serialize() / session.json
        :param pop: POP string (used for validation via pop_hash)
        :param verbose: verbose flag
        :return: Security1 instance with cipher at correct counter position, or None
        """
        try:
            shared_key = base64.b64decode(data['shared_key'])
            device_random = base64.b64decode(data['device_random'])
            ctr_offset = data['ctr_offset']
        except (KeyError, Exception):
            return None

        pop_bytes = str_to_bytes(pop) if pop else b''
        if data.get('pop_hash'):
            current_pop_hash = hashlib.sha256(pop_bytes).hexdigest() if len(pop_bytes) > 0 else ''
            if current_pop_hash != data['pop_hash']:
                return None

        obj = cls.__new__(cls)
        obj.pop = pop_bytes
        obj.verbose = verbose
        obj.session_state = security_state.FINISHED
        obj.shared_key = shared_key
        obj.device_random = device_random
        obj.ctr_offset = 0

        cipher = Cipher(algorithms.AES(shared_key), modes.CTR(device_random), backend=default_backend())
        obj.cipher = cipher.encryptor()

        if ctr_offset > 0:
            obj.cipher.update(b'\x00' * ctr_offset)
            obj.ctr_offset = ctr_offset

        Security.__init__(obj, obj.security1_session)
        return obj
