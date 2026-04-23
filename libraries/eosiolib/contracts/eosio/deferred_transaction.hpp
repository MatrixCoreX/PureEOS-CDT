/**
 *  @file
 *  @copyright defined in eos/LICENSE
 */
#pragma once
#include "system.hpp"
#include "transaction.hpp"
#include "../../core/eosio/serialize.hpp"

#include <vector>

namespace eosio {
   namespace internal_use_do_not_use {
      extern "C" {
         __attribute__((eosio_wasm_import))
         void send_deferred(const uint128_t&, uint64_t, const char*, size_t, uint32_t);

         __attribute__((eosio_wasm_import))
         int cancel_deferred(const uint128_t&);
      }
   }

  /**
   *  @defgroup deferred_transaction Transaction
   *  @ingroup contracts
   *  @brief Type-safe C++ wrappers for transaction C API
   *
   *  deferred_transaction is provided to support legacy EOS-style test contracts that
   *  use deferred transactions.
   *
   *  @details An inline message allows one contract to send another contract a message
   *  which is processed immediately after the current message's processing
   *  ends such that the success or failure of the parent transaction is
   *  dependent on the success of the message. If an inline message fails in
   *  processing then the whole tree of transactions and actions rooted in the
   *  block will me marked as failing and none of effects on the database will
   *  persist.
   *
   *  Inline actions and Deferred transactions must adhere to the permissions
   *  available to the parent transaction or, in the future, delegated to the
   *  contract account for future use.
   *
   *  @note There are some methods from the @ref transactioncapi that can be used directly from C++
   */

   /**
    *  Class transaction contains the actions, context_free_actions and extensions type for a transaction
    *
    *  @ingroup transaction
    */
   class deferred_transaction : public transaction {
   public:

      /**
       * Construct a new deferred_transaction with an expiration of now + 60 seconds.
       */
      deferred_transaction(time_point_sec exp = time_point_sec(current_time_point()) + 60) : transaction( exp ) {}

      /**
       *  Sends this transaction, packs the transaction then sends it as a deferred transaction
       *
       *  @details Writes the symbol_code as a string to the provided char buffer
       *  @param sender_id - ID of sender
       *  @param payer - Account paying for RAM
       *  @param replace_existing - Defaults to false, if this is `0`/false then if the provided sender_id is already in use by an in-flight transaction from this contract, which will be a failing assert. If `1` then transaction will atomically cancel/replace the inflight transaction
       */
      void send(const uint128_t& sender_id, name payer, bool replace_existing = false) const {
         auto serialize = pack(*static_cast<const transaction*>(this));
         internal_use_do_not_use::send_deferred(sender_id, payer.value, serialize.data(), serialize.size(), replace_existing);
      }

   };

   /**
    *  Struct onerror contains and sender id and packed transaction
    *
    *  @ingroup transaction
    */
   struct onerror {
      uint128_t          sender_id;
      std::vector<char> sent_trx;

     /**
      *  from_current_action unpacks and returns a onerror struct
      *
      *  @ingroup transaction
      */
      static onerror from_current_action() {
         return unpack_action_data<onerror>();
      }

     /**
      * Unpacks and returns a transaction
      */
      transaction unpack_sent_trx() const {
         return unpack<transaction>(sent_trx);
      }

      EOSLIB_SERIALIZE( onerror, (sender_id)(sent_trx) )
   };

   /**
    *  Send a deferred transaction
    *
    *  @ingroup transaction
    *  @param sender_id - Account name of the sender of this deferred transaction
    *  @param payer - Account name responsible for paying the RAM for this deferred transaction
    *  @param serialized_transaction - The packed transaction to be deferred
    *  @param size - The size of the packed transaction, required for persistence.
    *  @param replace - If true, will replace an existing transaction.
    */
   inline void send_deferred(const uint128_t& sender_id, name payer, const char* serialized_transaction, size_t size, bool replace = false) {
     internal_use_do_not_use::send_deferred(sender_id, payer.value, serialized_transaction, size, replace);
   }

    /**
     *  Cancels a deferred transaction.
     *
     *  @ingroup transaction
     *  @param sender_id - The id of the sender
     *
     *  @pre The deferred transaction ID exists.
     *  @pre The deferred transaction ID has not yet been published.
     *  @post Deferred transaction canceled.
     *
     *  @return 1 if transaction was canceled, 0 if transaction was not found
     *
     *  Example:
*
     *  @code
     *  id = 0xffffffffffffffff
     *  cancel_deferred( id );
     *  @endcode
     */
   inline int cancel_deferred(const uint128_t& sender_id) {
      return internal_use_do_not_use::cancel_deferred(sender_id);
   }
}
