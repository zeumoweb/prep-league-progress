#include <cstddef>
#include <stdexcept>
#include <new>
#include <utility>


template <typename T>
class Vector {
    private:
        size_t sz;
        size_t max_size;
        T* data = nullptr;
    public:
        explicit Vector() : sz(0), max_size(0) {}

        Vector(size_t n) : sz(n), max_size(n) {
            data = static_cast<T*>(::operator new(sizeof(T) * n));
            for (size_t i = 0; i < n; i++) {
                    ::new(static_cast<void*>(data + i)) T();
                }
        }

        ~Vector() {
            for (size_t i = 0; i < sz; i++) {
                    data[i].~T();
                }
            ::operator delete(data);
        }

        void push_back(const T& value) {
            if (sz == max_size) {
                // value may refer into our own buffer (e.g. push_back(v[0])), and resize() frees
                // that buffer, so copy it before growing.
                T copy(value);
                resize(max_size);
                ::new (static_cast<void*>(data + sz)) T(std::move(copy));
            } else {
                // Construct into raw memory; assigning with = would call operator= on no object.
                ::new (static_cast<void*>(data + sz)) T(value);
            }
            ++sz;
        }

        void push_back(T&& value) {
            if (sz == max_size){ resize(max_size); }
            ::new(static_cast<void*>(data + sz)) T(std::move(value)); sz++;
        }

        template <typename ...Args>
         T& emplace_back(Args&& ...args) {
            if (sz == max_size){
                resize(max_size);
            }
            ::new(static_cast<void*>(data + sz)) T(std::forward<Args>(args)...); sz++;
            return data[sz - 1];

        }

        size_t size() const noexcept{
            return sz;
        }

        size_t capacity() const noexcept{
            return max_size;
        }

        T& operator[](size_t index) {
            if (index < sz) {
            return data[index];}
            throw std::out_of_range("Index out of bound");
        }

        const T& operator[](size_t index) const {
            if (index < sz) {
            return data[index];}
            throw std::out_of_range("Index out of bound");
        }

        void reserve(size_t size) {
            if (size > max_size){
                resize(size);
                max_size = size;
            }
        }

        void resize(size_t new_size) {
                size_t new_max_size = new_size != max_size ? new_size : max_size ? max_size * 2 : 1;
                max_size = new_max_size;
                T* new_data = static_cast<T*>(::operator new(new_max_size * sizeof(T)));
                for (size_t i = 0; i < sz; i++){
                    ::new(static_cast<void*>( new_data + i)) T(data[i]);
                }

                for (size_t i = 0; i < sz; i++) {
                    data[i].~T();
                }

                ::operator delete(data);

                data = new_data;


        }
};

