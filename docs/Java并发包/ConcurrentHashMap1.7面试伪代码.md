# ConcurrentHashMap 1.7 版本面试伪代码

## 核心思想

**分段锁（Segment）**：将数据分成多个段，每个段独立加锁，多线程操作不同段时可以并发执行。

## 数据结构

三层结构：
```
ConcurrentHashMap
└── Segment[] (分段锁数组，默认16个)
    └── HashEntry[] (哈希桶数组)
        └── HashEntry链表
```

## 完整实现代码

```java
/**
 * ConcurrentHashMap 1.7 版本核心实现（面试半伪代码）
 * 核心思想：分段锁 Segment，每个Segment管理一部分数据
 */
public class ConcurrentHashMap<K, V> {

    // ========== 核心数据结构 ==========

    // Segment数组，每个Segment是一把锁
    final Segment<K,V>[] segments;

    // 默认并发级别（Segment数量）
    static final int DEFAULT_CONCURRENCY_LEVEL = 16;

    // ========== Segment：分段锁 ==========

    static class Segment<K,V> extends ReentrantLock {
        // 每个Segment内部维护一个HashEntry数组
        transient volatile HashEntry<K,V>[] table;
        transient int count;  // Segment中元素数量

        V put(K key, int hash, V value) {
            lock();  // 获取锁，只锁当前Segment
            try {
                // 1. 定位到数组索引（使用低位hash）
                // 低位hash用于定位Segment内部的数组索引
                int index = hash & (table.length - 1);
                HashEntry<K,V> first = table[index];

                // 2. 遍历链表，查找key是否存在
                HashEntry<K,V> e = first;
                while (e != null) {
                    if (e.hash == hash && key.equals(e.key)) {
                        V oldValue = e.value;
                        e.value = value;  // 更新值
                        return oldValue;
                    }
                    e = e.next;
                }

                // 3. key不存在，插入新节点（头插法）
                HashEntry<K,V> newNode = new HashEntry<>(hash, key, value, first);
                table[index] = newNode;
                count++;  // 元素数量+1

                // 4. 检查是否需要扩容
                if (count > threshold) {
                    rehash();
                }
                return null;
            } finally {
                unlock();
            }
        }

        V get(K key, int hash) {
            // 不加锁！利用volatile保证可见性
            if (count != 0) {
                int index = hash & (table.length - 1);
                HashEntry<K,V> e = table[index];

                while (e != null) {
                    if (e.hash == hash && key.equals(e.key)) {
                        return e.value;
                    }
                    e = e.next;
                }
            }
            return null;
        }

        void rehash() {
            // 扩容：创建新数组，容量翻倍
            HashEntry<K,V>[] oldTable = table;
            int oldCapacity = oldTable.length;
            int newCapacity = oldCapacity << 1;
            HashEntry<K,V>[] newTable = new HashEntry[newCapacity];

            // 重新hash所有元素
            for (int i = 0; i < oldCapacity; i++) {
                HashEntry<K,V> e = oldTable[i];
                while (e != null) {
                    HashEntry<K,V> next = e.next;
                    int index = e.hash & (newCapacity - 1);
                    e.next = newTable[index];
                    newTable[index] = e;
                    e = next;
                }
            }
            table = newTable;
        }
    }

    // ========== HashEntry：链表节点 ==========

    static class HashEntry<K,V> {
        final int hash;
        final K key;
        volatile V value;  // volatile保证可见性
        volatile HashEntry<K,V> next;

        HashEntry(int hash, K key, V value, HashEntry<K,V> next) {
            this.hash = hash;
            this.key = key;
            this.value = value;
            this.next = next;
        }
    }

    // ========== 对外API ==========

    public V put(K key, V value) {
        // 1. 计算hash
        int hash = hash(key);

        // 2. 定位Segment（使用高位hash）
        // 为什么用高位？
        // - hash >>> 28: 将32位hash的高4位移到最低位
        // - 高位定位Segment，低位定位数组索引，避免hash相近的key集中在同一Segment
        // - 这样可以让数据更分散，提高并发度
        // 示例：segments.length=16(2^4)需要4位，所以右移28位(32-4)
        int segmentIndex = (hash >>> 28) & (segments.length - 1);
        Segment<K,V> segment = segments[segmentIndex];

        // 3. 委托给Segment处理
        return segment.put(key, hash, value);
    }

    public V get(K key) {
        // 1. 计算hash
        int hash = hash(key);

        // 2. 定位Segment（使用高位hash）
        // 与put方法一样，用高位定位Segment
        int segmentIndex = (hash >>> 28) & (segments.length - 1);
        Segment<K,V> segment = segments[segmentIndex];

        // 3. 委托给Segment处理（不加锁）
        return segment.get(key, hash);
    }

    public int size() {
        // 多次尝试无锁统计
        final Segment<K,V>[] segments = this.segments;
        int size = 0;

        // 尝试2次无锁统计
        for (int k = 0; k < 2; k++) {
            int sum = 0;
            for (Segment<K,V> seg : segments) {
                sum += seg.count;
            }
            if (sum == size) {
                return size;  // 两次结果一致，返回
            }
            size = sum;
        }

        // 还不一致，就全部加锁统计
        for (Segment<K,V> seg : segments) {
            seg.lock();
        }
        try {
            size = 0;
            for (Segment<K,V> seg : segments) {
                size += seg.count;
            }
            return size;
        } finally {
            for (Segment<K,V> seg : segments) {
                seg.unlock();
            }
        }
    }

    // 简化的hash函数
    final int hash(Object k) {
        int h = k.hashCode();
        h ^= (h >>> 20) ^ (h >>> 12);
        return h ^ (h >>> 7) ^ (h >>> 4);
    }
}
```

## 核心要点（面试必答）

### 1. 分段锁机制
- 将数据分成16个Segment（默认），每个Segment独立加锁
- 多线程操作不同Segment时可以并发，提高性能
- 最大并发度 = Segment数量 = 16

### 2. put操作流程
```
计算hash → 定位Segment → 加锁 → 定位数组索引 → 遍历链表 → 插入/更新 → 释放锁
```
- **需要加锁**：只锁当前Segment，不影响其他Segment
- 头插法插入新节点
- 检查是否需要扩容（当前Segment独立扩容）

### 3. get操作流程
```
计算hash → 定位Segment → 定位数组索引 → 遍历链表 → 返回结果
```
- **不需要加锁**！利用volatile保证可见性
- HashEntry.value 和 next 都是 volatile
- 读操作效率高

### 4. size操作
- 先尝试2次无锁统计，两次结果一致就返回
- 如果两次结果不一致，说明有并发修改，全部加锁后统计
- 这是一种乐观的策略，大部分情况下不需要加锁

### 5. volatile的作用
```java
static class HashEntry<K,V> {
    final K key;
    volatile V value;      // 保证可见性
    volatile HashEntry<K,V> next;  // 保证可见性
}
```
- get操作不加锁，依赖volatile保证读取到最新值
- 一个线程修改value，其他线程能立即看到

### 6. 扩容机制
- **只扩容当前Segment**，不影响其他Segment
- 容量翻倍：oldCapacity << 1
- 重新hash所有元素到新数组

### 7. hash分层定位（重要！）

**为什么高位定位Segment，低位定位数组索引？**

```
32位hash值的分配：
┌────────┬────────────────────────────┐
│ 高4位  │         低28位              │
│ ▲      │          ▲                 │
│ │      │          │                 │
│ 定位   │        定位                 │
│Segment │       数组索引              │
└────────┴────────────────────────────┘

高位定位：segmentIndex = (hash >>> 28) & 15
低位定位：arrayIndex = hash & 15
```

**示例对比：**

```java
// ❌ 如果都用低位（错误做法）
hash1 = 0000...0001  → Segment[1], table[1]
hash2 = 0001...0001  → Segment[1], table[1]  // 集中在同一Segment！
hash3 = 0010...0001  → Segment[1], table[1]  // 并发度降低

// ✅ 高低分离（正确做法）
hash1 = 0000...0001  → Segment[0], table[1]
hash2 = 0001...0001  → Segment[1], table[1]  // 不同Segment，可并发！
hash3 = 0010...0001  → Segment[2], table[1]  // 不同Segment，可并发！
```

**核心优势：**
1. **避免冲突集中**：hash值相近的key分散到不同Segment
2. **提高并发度**：不同线程可以同时访问不同Segment
3. **充分利用hash**：高低位都利用，二次分散
4. **分层hash思想**：
   - 第一层：高位hash → 分散到不同Segment（粗粒度）
   - 第二层：低位hash → 分散到数组不同位置（细粒度）

## 优缺点分析

### 优点
✅ 并发度高：默认16个Segment，支持16个线程同时写入
✅ 读操作不加锁：get操作效率高
✅ 锁粒度细：只锁当前Segment，不影响其他Segment

### 缺点
❌ 最大并发度受限：最多16个线程并发写
❌ 扩容复杂：每个Segment独立扩容，不能全局扩容
❌ 内存占用：需要维护多个Segment和HashEntry数组
❌ size操作复杂：可能需要全部加锁

## 与1.8版本对比

| 特性 | 1.7版本 | 1.8版本 |
|------|---------|---------|
| 核心结构 | Segment + HashEntry | Node数组 + 链表/红黑树 |
| 锁机制 | ReentrantLock (Segment锁) | synchronized (桶锁) + CAS |
| 最大并发度 | Segment数量（默认16） | 数组长度（默认16，可扩容） |
| 扩容 | Segment独立扩容 | 全局扩容，支持多线程协助 |
| 红黑树 | 无 | 链表长度>8转红黑树 |
| 性能 | 好 | 更好（JDK优化了synchronized） |

## 面试常见问题

### Q1: 为什么get不需要加锁？
**A:** 因为HashEntry的value和next都是volatile的，保证了可见性。一个线程修改后，其他线程能立即看到最新值。

### Q2: ConcurrentHashMap是如何保证线程安全的？
**A:**
- put操作：加Segment锁，只锁当前段
- get操作：利用volatile保证可见性，不加锁
- size操作：先尝试无锁统计，不一致就全部加锁

### Q3: 为什么1.8要放弃Segment？
**A:**
- Segment限制了最大并发度（默认16）
- 1.8改用synchronized（JVM优化后性能更好）+ CAS
- 1.8支持更细粒度的锁（每个桶一把锁）
- 1.8支持红黑树，性能更好

### Q4: Segment继承ReentrantLock有什么好处？
**A:**
- Segment本身就是一把锁，不需要额外的锁对象
- 减少内存占用
- 加锁代码更简洁：直接调用lock()/unlock()

### Q5: 为什么使用头插法而不是尾插法？
**A:**
- 头插法效率高，O(1)时间复杂度
- 不需要遍历到链表尾部
- 新插入的数据可能更容易被访问（局部性原理）
