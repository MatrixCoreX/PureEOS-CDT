// Count actual SDK cache comparisons; mock storage is not a blockchain or TPS test.
#include <cstdint>
#include <cstdio>
#include <eosio/multi_index.hpp>
#include <eosio/intrinsics.hpp>
static uint64_t comparisons = 0, host_stores = 0, host_reads = 0;
struct row {
   uint64_t id = 0, value = 0;
   uint64_t primary_key() const { ++comparisons; return id; }
   EOSLIB_SERIALIZE(row, (id)(value))
};
using rows = eosio::multi_index<"cacheprofile"_n, row>;
int main() {
   using host = eosio::native::intrinsics;
   host::set_intrinsic<host::current_receiver>([] { return "cachebench"_n.value; });
   host::set_intrinsic<host::db_store_i64>([](auto...) { return int32_t(++host_stores); });
   host::set_intrinsic<host::db_find_i64>([](auto...) { ++host_reads; return int32_t(-1); });
   host::set_intrinsic<host::db_get_i64>([](auto...) { ++host_reads; return int32_t(-1); });
   for (unsigned round = 1; round <= 3; ++round)
   for (uint64_t count : {uint64_t(1), uint64_t(8), uint64_t(64), uint64_t(1024)}) {
      rows table("cachebench"_n, round * 10000 + count);
      for (uint64_t i = 0; i < count; ++i) table.emplace("cachebench"_n, [&](auto& item) { item.id = i; item.value = i + 7; });
      comparisons = host_reads = 0;
      for (uint64_t i = 0; i < count; ++i)
         if (table.find(i)->value != i + 7) return 1;
      const auto finds = comparisons;
      comparisons = 0;
      for (uint64_t i = 0; i < count; ++i)
         if (table.require_find(i)->value != i + 7) return 1;
      const auto expected = count * (count + 1) / 2;
      if (finds != expected || comparisons != expected || host_reads) return 1;
      std::printf("{\"round\":%u,\"rows\":%llu,\"find_comparisons\":%llu,\"require_find_comparisons\":%llu,\"host_reads\":%llu}\n",
         round, (unsigned long long)count, (unsigned long long)finds, (unsigned long long)comparisons, (unsigned long long)host_reads);
   }
}
