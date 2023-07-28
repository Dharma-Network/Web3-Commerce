from pyteal import *


class Constants:
    admin_init = Bytes("admin_init")
    order_new = Bytes("order_new")
    order_new_phygital = Bytes("order_new_phygital")
    order_review = Bytes("order_review")
    collection_init = Bytes("collection_init")
    phygital_product_withdraw = Bytes("phygital_product_widthdraw")
    phygital_preminted_optin = Bytes("phygital_preminted_optin")
    phygital_preminted_withdraw_owner = Bytes(
        "phygital_preminted_withdraw_owner")


@Subroutine(TealType.none)
def init_app():
    pos_fees = Txn.application_args[1]
    oraclePubKey = Txn.application_args[2]
    targetAssets = Txn.assets.length()
    i = ScratchVar(TealType.uint64)

    Assert(Txn.sender() == Global.creator_address())

    return Seq([
        App.globalPut(Bytes("posFees"), pos_fees),
        App.globalPut(Bytes("oraclePubKey"), oraclePubKey),
        i.store(Int(0)),
        While(i.load() < targetAssets).Do(
            # optin txn
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_amount: Int(0),
                TxnField.xfer_asset: Txn.assets[i.load()],
                TxnField.sender: Global.current_application_address(),
                TxnField.asset_receiver: Global.current_application_address(),

            }),
            InnerTxnBuilder.Submit(),
            i.store(i.load() + Int(1))
        )
    ])


@Subroutine(TealType.bytes)
def int_to_ascii(arg):
    """int_to_ascii converts an integer to the ascii byte that represents it"""
    return Extract(Bytes("0123456789"), arg, Int(1))


@Subroutine(TealType.bytes)
def getAssetCreator():
    """get the creator address of foreign asset[0]"""
    assetCreator = AssetParam.creator(Txn.assets[0])
    return Seq(
        assetCreator,
        Assert(assetCreator.hasValue()),
        assetCreator.value()
    )


@Subroutine(TealType.bytes)
def itoa(i):
    """itoa converts an integer to the ascii byte string it represents"""
    return If(
        i == Int(0),
        Bytes("0"),
        Concat(
            If(i / Int(10) > Int(0), itoa(i / Int(10)), Bytes("")),
            int_to_ascii(i % Int(10)),
        ),
    )


@ Subroutine(TealType.none)
def phygital_withdraw():

    assetName = AssetParam.name(Txn.assets[0])
    assetHash = AssetParam.metadataHash(Txn.assets[0])

    return Seq(
        assetName,
        assetHash,
        Assert(Sha256(Txn.sender()) == assetHash.value()),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: Txn.assets[0],
            TxnField.asset_receiver: Txn.sender(),
            TxnField.asset_amount: Int(1),
            TxnField.note: Concat(Bytes("Withdraw:"), assetName.value())
        }),
        InnerTxnBuilder.Submit(),
    )


@ Subroutine(TealType.none)
def phygital_mint():
    collection_name = Txn.application_args[11]
    collection_type = Txn.application_args[10]
    merchant_pubkey = Txn.application_args[1]
    merchant_address_bytes = Txn.application_args[9]

    baseBox = Sha256(
        Concat(collection_name, merchant_pubkey, merchant_address_bytes, collection_type))

    collectionMintedAmount = Concat(baseBox, Bytes("A"))
    collectionMaxSupply = Concat(baseBox, Bytes("B"))
    collectionFirstValid = Concat(baseBox, Bytes("C"))
    collectionLastValid = Concat(baseBox, Bytes("D"))
    collectionImageUrl = Concat(baseBox, Bytes("E"))

    Seq(
        collection_box_check := App.box_length(collectionMintedAmount),
        Assert(collection_box_check.hasValue()),
    )

    minted = App.box_get(collectionMintedAmount)
    max_supply = App.box_get(collectionMaxSupply)
    last_valid = App.box_get(collectionLastValid)
    first_valid = App.box_get(collectionFirstValid)
    image_url = App.box_get(collectionImageUrl)

    return Seq([
        minted,
        max_supply,
        last_valid,
        first_valid,
        image_url,
        # If(
        #    Global.round() > Btoi(last_valid.value())
        # ).Then(
        #    Reject()
        # ),
        # If(
        #    Global.round() < Btoi(first_valid.value())
        # ).Then(
        #    Reject()
        # ),
        If(Btoi(max_supply.value()) == Int(000)).Then(
            # only product tokenization for authenticity
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: Int(1),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_unit_name: Concat(Bytes("PHY"), itoa(Add(Btoi(minted.value())+Int(1)))),
                TxnField.config_asset_name: Concat(collection_name, Bytes(" #"), itoa(Add(Btoi(minted.value())+Int(1)))),
                TxnField.config_asset_url: image_url.value(),
                TxnField.config_asset_metadata_hash: Sha256(Txn.sender()),
                TxnField.config_asset_reserve: merchant_address_bytes,
            }),
            InnerTxnBuilder.Submit(),
            App.box_put(collectionMintedAmount,
                        Itob(Btoi(minted.value()) + Int(1))),
        ).ElseIf(Btoi(minted.value()) < Btoi(max_supply.value())).Then(
            # create NFT limited edition for the product
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: Int(1),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_unit_name: Concat(Bytes("PHY"), itoa(Add(Btoi(minted.value())+Int(1)))),
                TxnField.config_asset_name: Concat(collection_name, Bytes(" #"), itoa(Add(Btoi(minted.value())+Int(1)))),
                TxnField.config_asset_url: image_url.value(),
                TxnField.config_asset_metadata_hash: Sha256(Txn.sender()),
                TxnField.config_asset_reserve: merchant_address_bytes,
            }),
            InnerTxnBuilder.Submit(),

            App.box_put(collectionMintedAmount,
                        Itob(Btoi(minted.value()) + Int(1))),

        ).Else(
            Reject()
        )
    ])


@ Subroutine(TealType.none)
def collection_init():
    collection_name = Txn.application_args[1]
    merchant_pubkey = Txn.application_args[2]
    collection_max_supply = Txn.application_args[3]
    collection_first_valid = Txn.application_args[4]
    collection_last_valid = Txn.application_args[5]
    collection_image_url = Txn.application_args[6]
    collection_requirement_type = Txn.application_args[7]
    collection_requirement_ID = Txn.application_args[8]
    # phygital, tokengate, phygitaltokengate
    collection_type = Txn.application_args[9]

    fees_calculator = ScratchVar(TealType.uint64)

    baseBox = Sha256(Concat(collection_name, merchant_pubkey,
                     Txn.sender(), collection_type))

    fees_payment = Gtxn[1]

    collectionMintedAmount = Concat(baseBox, Bytes("A"))
    collectionMaxSupply = Concat(baseBox, Bytes("B"))
    collectionFirstValid = Concat(baseBox, Bytes("C"))
    collectionLastValid = Concat(baseBox, Bytes("D"))
    collectionImageUrl = Concat(baseBox, Bytes("E"))
    collectionrequirementTypeBoxName = Concat(baseBox, Bytes("F"))
    collectionrequirementIDBoxName = Concat(baseBox, Bytes("G"))

    return Seq([
        fees_calculator.store(Mul(Int(2500), Int(7))),
        fees_calculator.store(Mul(Int(400), Len(Concat(
            collectionMintedAmount, collectionMaxSupply, collectionLastValid, collectionImageUrl)))),

        Assert(fees_payment.amount() >= fees_calculator.load()),
        Assert(fees_payment.receiver() == Global.current_application_address()),

        App.box_put(collectionMintedAmount, Itob(Int(0))),
        App.box_put(collectionMaxSupply, collection_max_supply),
        App.box_put(collectionFirstValid, collection_first_valid),
        App.box_put(collectionLastValid, collection_last_valid),
        App.box_put(collectionImageUrl, collection_image_url),
        App.box_put(collectionrequirementTypeBoxName,
                    collection_requirement_type),
        App.box_put(collectionrequirementIDBoxName, collection_requirement_ID),
    ])


@ Subroutine(TealType.none)
def verify_tokengate():
    collection_name = Txn.application_args[11]
    collection_type = Txn.application_args[10]
    merchant_pubkey = Txn.application_args[1]
    merchant_address_bytes = Txn.application_args[9]

    gateKey = Txn.assets[0]

    baseBox = Sha256(
        Concat(collection_name, merchant_pubkey, merchant_address_bytes, collection_type))

    requirementTypeBoxName = Concat(baseBox, Bytes("F"))
    requirementIDBoxName = Concat(baseBox, Bytes("G"))

    requirementType = App.box_get(requirementTypeBoxName)
    requirementID = App.box_get(requirementIDBoxName)

    customerHolding = AssetHolding.balance(Txn.sender(), gateKey)
    assetCreator = AssetParam.creator(gateKey)
    assetReserve = AssetParam.reserve(gateKey)

    return Seq([
        requirementType,
        requirementID,
        customerHolding,
        assetCreator,
        assetReserve,
        If(requirementType.value() == Bytes("NFT Membership")).Then(
            Assert(assetCreator.value() == requirementID.value()),
            Assert(customerHolding.value() == Int(1))
        ).ElseIf(requirementType.value() == Bytes("NFT Membership V2")).Then(
            Assert(assetReserve.value() == requirementID.value()),
            Assert(customerHolding.value() == Int(1))
        ).ElseIf(requirementType.value() == Bytes("NFT Ownership")).Then(
            Assert(gateKey == Btoi(requirementID.value())),
            Assert(customerHolding.value() == Int(1))
        ).ElseIf(requirementType.value() == Bytes("Token Ownership")).Then(
            Assert(gateKey == Btoi(requirementID.value())),
            Assert(customerHolding.value() >= Int(1))
        )
    ])


@ Subroutine(TealType.none)
def verify_OraclesCommittee():
    proofData = Txn.application_args[1]
    pubKey = Txn.application_args[2]
    Assert(
        VrfVerify.algorand(
            message=Bytes("node1,node2,node3"),
            proof=proofData,
            public_key=pubKey
        ))


@ Subroutine(TealType.none)
def customer_new_orderV2():

    opup = OpUp(OpUpMode.OnCall)
    opup.maximize_budget(Int(10000))

    current_round = Global.round()

    merchant_pubkey = Txn.application_args[1]  # public key of merchant

    product_id = Txn.application_args[2]  # product id
    product_id_price = Txn.application_args[3]
    product_id_signature = Txn.application_args[4]  # product id signature

    merchant_address = Txn.application_args[5]  # oracle data

    oracle_round = Txn.application_args[6]  # oracle round data
    oracle_data_signature = Txn.application_args[7]  # oracle data signature

    oraclePubKey = App.globalGetEx(
        Global.current_application_id(), Bytes("oraclePubKey"))

    oracle_data_verify = ScratchVar(TealType.bytes)
    product_id_data_verify = ScratchVar(TealType.bytes)
    payment_type_data_verify = ScratchVar(TealType.bytes)

    payment_type_signature = Txn.application_args[8]  # payment amount
    merchant_address_bytes = Txn.application_args[9]
    collection_type = Txn.application_args[10]
    collection_name = Txn.application_args[11]

    merchant_payment_txn = Gtxn[9]
    merchant_paymentType = merchant_payment_txn.type_enum()
    pos_payment_txn = Gtxn[14]

    Assert(
        And(
            Btoi(oracle_round) >= Minus(current_round, Int(4)),
            Btoi(oracle_round) <= current_round
        )
    )

    return Seq([
        oraclePubKey,
        Assert(oraclePubKey.hasValue()),
        product_id_data_verify.store(
            Concat(product_id, product_id_price, collection_type, collection_name)),  # collection_type could be null if the product is not connected to a collection
        If(merchant_paymentType == TxnType.Payment).Then(

            payment_type_data_verify.store(
                Concat(Bytes("L1"), merchant_address)),

            oracle_data_verify.store(
                Concat(
                    product_id_price,
                    Bytes("L1"),
                    Itob(Add(merchant_payment_txn.amount(),
                         pos_payment_txn.amount())),
                    oracle_round,
                )),

            Assert(Ed25519Verify_Bare(payment_type_data_verify.load(),
                                      payment_type_signature, merchant_pubkey)),

            Assert(Ed25519Verify_Bare(oracle_data_verify.load(),
                                      oracle_data_signature, oraclePubKey.value())),

            Assert(Ed25519Verify_Bare(
                product_id_data_verify.load(), product_id_signature, merchant_pubkey)),

            If(collection_type == Bytes("phygital")).Then(
                phygital_mint(),
                verify_payments()
            ).ElseIf(collection_type == Bytes("tokengate")).Then(
                verify_tokengate(),
                verify_payments()
            ).ElseIf(collection_type == Bytes("tokengatephygital")).Then(
                phygital_mint(),
                verify_tokengate(),
                verify_payments()
            ).ElseIf(collection_type == Bytes("false")).Then(
                verify_payments()
            )

        ).ElseIf(merchant_paymentType == TxnType.AssetTransfer).Then(

            payment_type_data_verify.store(
                Concat(Itob(merchant_payment_txn.xfer_asset()), merchant_address)),

            oracle_data_verify.store(
                Concat(
                    product_id_price,
                    Itob(merchant_payment_txn.xfer_asset()),
                    Itob(Add(merchant_payment_txn.asset_amount(),
                         pos_payment_txn.asset_amount())),
                    oracle_round,
                )),

            Assert(Ed25519Verify_Bare(payment_type_data_verify.load(),
                                      payment_type_signature, merchant_pubkey)),

            Assert(Ed25519Verify_Bare(oracle_data_verify.load(),
                                      oracle_data_signature, oraclePubKey.value())),

            Assert(Ed25519Verify_Bare(
                product_id_data_verify.load(), product_id_signature, merchant_pubkey)),


            If(collection_type == Bytes("phygital")).Then(
                phygital_mint(),
                verify_payments()
            ).ElseIf(collection_type == Bytes("tokengate")).Then(
                verify_tokengate(),
                verify_payments()
            ).ElseIf(collection_type == Bytes("tokengatephygital")).Then(
                phygital_mint(),
                verify_tokengate(),
                verify_payments()
            ).ElseIf(collection_type == Bytes("false")).Then(
                verify_payments()
            )

        ),
    ])


@ Subroutine(TealType.none)
def verify_payments():

    merchant_address_bytes = Txn.application_args[9]
    merchant_payment_txn = Gtxn[9]
    pos_payment_txn = Gtxn[14]
    pos_paymentType = pos_payment_txn.type_enum()
    merchant_paymentType = merchant_payment_txn.type_enum()

    fullAmount = ScratchVar(TealType.uint64)
    serviceFee = ScratchVar(TealType.uint64)
    merchantPayment = ScratchVar(TealType.uint64)

    posFee = App.globalGetEx(Global.current_application_id(), Bytes("posFees"))

    return Seq(
        posFee,
        Assert(posFee.hasValue()),
        Assert(merchant_payment_txn.sender() == Gtxn[0].sender()),
        Assert(merchant_paymentType == pos_paymentType),

        If(
            merchant_paymentType == TxnType.Payment).Then(
            Assert(merchant_payment_txn.receiver() == merchant_address_bytes),
            Assert(pos_payment_txn.receiver() ==
                   Global.current_application_address()),
                fullAmount.store(
                    Add(merchant_payment_txn.amount(), pos_payment_txn.amount())),
                serviceFee.store(
                    Mul(fullAmount.load(), Btoi(posFee.value())) / Int(100)),
                merchantPayment.store(
                    Minus(fullAmount.load(), serviceFee.load())),
                Assert(merchantPayment.load() ==
                       merchant_payment_txn.amount()),
                Assert(serviceFee.load() == pos_payment_txn.amount())
        ).ElseIf(merchant_paymentType == TxnType.AssetTransfer).Then(
            Assert(merchant_payment_txn.asset_receiver()
                   == merchant_address_bytes),
            Assert(pos_payment_txn.asset_receiver() ==
                   Global.current_application_address()),
            fullAmount.store(
                Add(merchant_payment_txn.asset_amount(), pos_payment_txn.asset_amount())),
            serviceFee.store(
                Mul(fullAmount.load(), Btoi(posFee.value())) / Int(100)),
            merchantPayment.store(Minus(fullAmount.load(), serviceFee.load())),
            # Assert(merchantPayment.load() ==
            #       merchant_payment_txn.asset_amount()),
            #    Assert(serviceFee.load() == pos_payment_txn.asset_amount())
        )
    )


@ Subroutine(TealType.none)
def customer_review_order():

    merchant_ID = Txn.application_args[1]

    merchant_store_address = Txn.application_args[2]

    business_name = Concat(merchant_ID, merchant_store_address)

    order_review_text = Txn.application_args[3]
    order_review_stars = Txn.application_args[4]
    order_review_ID = Concat(Bytes("review_customer_order"),
                             Bytes("_"), business_name)

    return Seq(
        # check that merchant store exists
        merchant_store_check := App.box_length(business_name),
        Assert(merchant_store_check.hasValue()),
        Assert(Len(order_review_text) > Int(1)),
        Assert(Int(0) <= Len(order_review_stars) <= Int(5)),
        Assert(Gtxn[0].note() == order_review_ID),
        Approve()
    )


def approval_program():

    initialize = Seq([
        Assert(Txn.type_enum() == TxnType.ApplicationCall),
        Assert(Txn.application_args.length() == Int(0)),
        Approve()
    ])

    new_order = Seq(
        Assert(Txn.close_remainder_to() == Global.zero_address()),
        Assert(Txn.rekey_to() == Global.zero_address()),
        customer_new_orderV2(),
        Approve()
    )

    review_order = Seq(
        Assert(Txn.close_remainder_to() == Global.zero_address()),
        Assert(Txn.rekey_to() == Global.zero_address()),
        customer_review_order(),
        Approve()
    )

    init_collection = Seq(
        Assert(Txn.close_remainder_to() == Global.zero_address()),
        Assert(Txn.rekey_to() == Global.zero_address()),
        collection_init(),
        Approve()
    )

    withdraw_phygital_product = Seq(
        Assert(Txn.close_remainder_to() == Global.zero_address()),
        Assert(Txn.rekey_to() == Global.zero_address()),
        phygital_withdraw(),
        Approve()
    )

    app_init = Seq(
        Assert(Txn.close_remainder_to() == Global.zero_address()),
        Assert(Txn.rekey_to() == Global.zero_address()),
        init_app(),
        Approve()
    )

    onCall = If(Txn.application_args[0] == Constants.order_new).Then(new_order)  \
        .ElseIf(Txn.application_args[0] == Constants.order_review).Then(review_order)  \
        .ElseIf(Txn.application_args[0] == Constants.collection_init).Then(init_collection)  \
        .ElseIf(Txn.application_args[0] == Constants.phygital_product_withdraw).Then(withdraw_phygital_product)  \
        .ElseIf(Txn.application_args[0] == Constants.admin_init).Then(app_init)  \
        .Else(Approve())

    return If(Txn.application_id() == Int(0)).Then(initialize)                  \
        .ElseIf(Txn.on_completion() == OnComplete.CloseOut).Then(Reject()) \
        .ElseIf(Txn.on_completion() == OnComplete.UpdateApplication).Then(Reject()) \
        .ElseIf(Txn.on_completion() == OnComplete.DeleteApplication).Then(Reject()) \
        .ElseIf(Txn.on_completion() == OnComplete.ClearState).Then(Reject()) \
        .ElseIf(Txn.on_completion() == OnComplete.OptIn).Then(Approve())    \
        .ElseIf(Txn.on_completion() == Int(0)).Then(onCall)                 \
        .Else(Reject())


def clear_program():
    return Approve()


if __name__ == "__main__":
    with open("approval.teal", "w+") as f:
        compiled = compileTeal(
            approval_program(), mode=Mode.Application, version=8)
        f.write(compiled)

    with open("clear.teal", "w+") as f:
        compiled = compileTeal(
            clear_program(), mode=Mode.Application, version=8)
        f.write(compiled)
