import base64
from typing import List
from solana.publickey import PublicKey

from solders.instruction import AccountMeta, Instruction
from solders.message import Message as SoldersMessage
from solders.pubkey import Pubkey

from spl.token.instructions import get_associated_token_address, SetAuthorityParams, AuthorityType
from spl.token._layouts import INSTRUCTIONS_LAYOUT, InstructionType

from kinetic_sdk.helpers.sign_and_serialize_transaction import sign_and_serialize_transaction

from kinetic_sdk.models.constants import ASSOCIATED_TOKEN_PROGRAM_ID
from kinetic_sdk.models.constants import SYSTEM_PROGRAM_PROGRAM_ID
from kinetic_sdk.models.constants import SYSVAR_RENT_PUBKEY
from kinetic_sdk.models.constants import TOKEN_PROGRAM_ID
from kinetic_sdk.models.constants import PROGRAM_KEY

from kinetic_sdk.models.public_key_string import PublicKeyString
from kinetic_sdk.models.keypair import Keypair
from kinetic_sdk.models.kin_memo import KinMemo
from kinetic_sdk.models.transaction_type import TransactionType

def create_associated_token_account_instruction(
    payer: Pubkey,
    associated_token: Pubkey,
    owner: Pubkey,
    mint: Pubkey):
    
    account_metas = [
        AccountMeta(payer, True, True),
        AccountMeta(associated_token, False, True),
        AccountMeta(owner, False, False),
        AccountMeta(mint, False, False),
        AccountMeta(SYSTEM_PROGRAM_PROGRAM_ID, False, False),
        AccountMeta(TOKEN_PROGRAM_ID, False, False),
        AccountMeta(SYSVAR_RENT_PUBKEY, False, False),
    ]
    
    return Instruction(
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
        data=bytes(0),
        accounts=account_metas
    )

def create_memo_program(app_index: int):
    return Instruction(
        program_id=PROGRAM_KEY,
        data=bytes(base64.b64encode(KinMemo.new(1, TransactionType.NONE, app_index, b'').val).decode('utf-8'), 'utf-8'),
        accounts=[]
    )

def __add_signers(keys: List[AccountMeta], owner: PublicKey, signers: List[PublicKey]) -> None:
    if signers:
        keys.append(AccountMeta(pubkey=owner, is_signer=False, is_writable=False))
        for signer in signers:
            keys.append(AccountMeta(pubkey=signer, is_signer=True, is_writable=False))
    else:
        keys.append(AccountMeta(pubkey=owner, is_signer=True, is_writable=False))

def create_set_authority(owner: PublicKey, associated_token_account: PublicKey, mint_fee_payer: PublicKey):
    
    params = SetAuthorityParams(
        program_id=TOKEN_PROGRAM_ID,
        account=associated_token_account.to_solders(),
        authority=AuthorityType.CLOSE_ACCOUNT,
        current_authority=owner.to_solders(),
        new_authority=mint_fee_payer.to_solders()
    )
    new_authority, opt = (params.new_authority, 1) if params.new_authority else (PublicKey(0), 0)
    data = INSTRUCTIONS_LAYOUT.build(
        dict(
            instruction_type=InstructionType.SET_AUTHORITY,
            args=dict(authority_type=params.authority, new_authority_option=opt, new_authority=bytes(new_authority)),
        )
    )
    keys = [AccountMeta(pubkey=params.account, is_signer=False, is_writable=True)]
    __add_signers(keys, params.current_authority, params.signers)
    return Instruction(
        program_id=params.program_id,
        data=data,
        accounts=keys
    )
    
def generate_create_account_transaction(
        add_memo: bool,
        app_index: int,
        recent_blockhash: str,
        mint_fee_payer: PublicKeyString,
        mint_public_key: PublicKeyString,
        owner: Keypair,
):
    associated_token_account = get_associated_token_address(
        owner.public_key,
        PublicKey(mint_public_key)
    )

    instructions = list()
    instructions.append(create_memo_program(app_index))
    
    instructions.append(create_associated_token_account_instruction(
        payer=PublicKey(mint_fee_payer).to_solders(),
        associated_token=associated_token_account.to_solders(),
        owner=owner.public_key.to_solders(),
        mint=PublicKey(mint_public_key).to_solders()
    ))
    
    instructions.append(create_set_authority(
        owner.public_key,
        associated_token_account,
        PublicKey(mint_fee_payer)
    ))
    message = SoldersMessage(instructions, owner.to_solders().pubkey())

    return sign_and_serialize_transaction(message, mint_fee_payer, owner, recent_blockhash)
