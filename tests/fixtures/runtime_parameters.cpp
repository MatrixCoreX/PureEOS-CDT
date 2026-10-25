#include <eosio/eosio.hpp>
#include <eosio/privileged.hpp>
#include <eosio/serialize.hpp>
#include <cstring>

// Privileged test contract only. The native test creates a private genesis,
// checks every serialized v0 field and verifies restoration of the complete
// native configuration. This never changes a running user's chain.
class [[eosio::contract("rtparams")]] runtimeparams : public eosio::contract {
public:
   using contract::contract;

   [[eosio::action]] void verify(uint32_t expected_cpu, uint64_t expected_net) {
      eosio::require_auth(get_self());
      const auto read_direct = [] {
         const auto needed = eosio::internal_use_do_not_use::get_blockchain_parameters_packed(nullptr, 0);
         eosio::check(needed == 68, "unexpected native parameter wire size");
         std::vector<char> bytes(needed);
         const auto written = eosio::internal_use_do_not_use::get_blockchain_parameters_packed(
            bytes.data(), uint32_t(bytes.size()));
         eosio::check(written == needed, "native parameter wire truncated");
         return bytes;
      };
      const auto original = read_direct();
      eosio::blockchain_parameters parameters{};
      eosio::get_blockchain_parameters(parameters);
      eosio::check(parameters.max_block_cpu_usage == expected_cpu &&
                   parameters.max_block_net_usage == expected_net,
                   "SDK parameter deserialization differs from native configuration");
      eosio::check(eosio::pack(parameters) == original,
                   "SDK parameter fields differ from native wire");

      // Exercise the SDK serializer too. All v0 fields except this bounded CPU
      // change must survive, as must the v1/v2 fields checked by the native test.
      parameters.max_block_cpu_usage += 1000;
      eosio::set_blockchain_parameters(parameters);
      eosio::check(read_direct() == eosio::pack(parameters),
                   "SDK parameter setter differs from native wire");
      eosio::blockchain_parameters updated{};
      eosio::get_blockchain_parameters(updated);
      eosio::check(eosio::pack(updated) == eosio::pack(parameters),
                   "SDK parameter get/set round trip differs");

      const auto restore = eosio::unpack<eosio::blockchain_parameters>(original);
      eosio::set_blockchain_parameters(restore);
      eosio::check(read_direct() == original, "native parameter restoration differs");
   }
};

EOSIO_DISPATCH(runtimeparams, (verify))
