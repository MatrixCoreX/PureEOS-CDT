#include <eosio/tester.hpp>
#include <eosio/intrinsics.hpp>
#include <eosio/privileged.hpp>
#include <eosio/serialize.hpp>
#include <cstring>
#include <vector>
#include <type_traits>

static_assert(std::is_same_v<eosio::internal_use_do_not_use::capi_checksum256, ::capi_checksum256>);
static_assert(sizeof(::capi_checksum256) == 32 && alignof(::capi_checksum256) == 16);

// Native SDK library regression. The separate real-controller WASM fixture
// checks these APIs against consensus; these callbacks only supply known bytes.
EOSIO_TEST_BEGIN(runtime_parameter_round_trip)
   using intrinsics = eosio::native::intrinsics;
   eosio::blockchain_parameters expected{};
   expected.max_block_net_usage = 2097152;
   expected.target_block_net_usage_pct = 2000;
   expected.max_transaction_net_usage = 524288;
   expected.base_per_transaction_net_usage = 12;
   expected.net_usage_leeway = 700;
   expected.context_free_discount_net_usage_num = 3;
   expected.context_free_discount_net_usage_den = 7;
   expected.max_block_cpu_usage = 321000;
   expected.target_block_cpu_usage_pct = 1500;
   expected.max_transaction_cpu_usage = 151000;
   expected.min_transaction_cpu_usage = 101;
   expected.max_transaction_lifetime = 3601;
   expected.deferred_trx_expiration_window = 601;
   expected.max_transaction_delay = 1000;
   expected.max_inline_action_size = 4097;
   expected.max_inline_action_depth = 5;
   expected.max_authority_depth = 7;
   auto wire = eosio::pack(expected);
   REQUIRE_EQUAL(wire.size(), size_t(68))
   const auto previous_get = intrinsics::get_intrinsic<intrinsics::get_blockchain_parameters_packed>();
   const auto previous_set = intrinsics::get_intrinsic<intrinsics::set_blockchain_parameters_packed>();
   intrinsics::set_intrinsic<intrinsics::get_blockchain_parameters_packed>(
      [&](char* data, uint32_t size) -> uint32_t {
         if (!size) return uint32_t(wire.size());
         if (size < wire.size()) return 0;
         std::memcpy(data, wire.data(), wire.size());
         return uint32_t(wire.size());
      });
   intrinsics::set_intrinsic<intrinsics::set_blockchain_parameters_packed>(
      [&](char* data, uint32_t size) { wire.assign(data, data + size); });
   eosio::blockchain_parameters actual{};
   eosio::get_blockchain_parameters(actual);
   const bool read_matches = eosio::pack(actual) == wire;
   actual.max_block_cpu_usage += 1000;
   eosio::set_blockchain_parameters(actual);
   const bool write_matches = wire == eosio::pack(actual);
   eosio::blockchain_parameters again{};
   eosio::get_blockchain_parameters(again);
   const bool round_trip_matches = eosio::pack(again) == wire;
   intrinsics::set_intrinsic<intrinsics::get_blockchain_parameters_packed>(previous_get);
   intrinsics::set_intrinsic<intrinsics::set_blockchain_parameters_packed>(previous_set);
   REQUIRE_EQUAL(read_matches, true)
   REQUIRE_EQUAL(write_matches, true)
   REQUIRE_EQUAL(round_trip_matches, true)
EOSIO_TEST_END

int main() {
   silence_output(false);
   EOSIO_TEST(runtime_parameter_round_trip)
   return has_failed();
}
