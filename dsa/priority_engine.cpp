#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

using namespace std;

struct Complaint {
    int id;
    string room;
    string category;
    int urgency;
    int age;
    int score;
};

int get_category_weight(string cat) {
    if (cat == "Electricity" || cat == "Water") return 5;
    if (cat == "Food") return 4;
    if (cat == "WiFi") return 3;
    return 2; // Room maintenance
}

void calculate_scores(vector<Complaint>& list) {
    map<string, int> freq_map;
    for (auto& c : list) freq_map[c.room + c.category]++;

    for (auto& c : list) {
        int cat_w = get_category_weight(c.category);
        int freq_bonus = (freq_map[c.room + c.category] >= 3) ? 3 : 0;
        c.score = (c.urgency * 5) + (cat_w * 3) + (c.age * 2) + freq_bonus;
    }
}

// Max-Heap logic for priority
void heapify(vector<Complaint>& arr, int n, int i) {
    int largest = i;
    int l = 2 * i + 1;
    int r = 2 * i + 2;
    if (l < n && arr[l].score > arr[largest].score) largest = l;
    if (r < n && arr[r].score > arr[largest].score) largest = r;
    if (largest != i) {
        swap(arr[i], arr[largest]);
        heapify(arr, n, largest);
    }
}

int main() {
    vector<Complaint> complaints;
    int id, urg, age;
    string room, cat;

    while (cin >> id >> room >> cat >> urg >> age) {
        complaints.push_back({id, room, cat, urg, age, 0});
    }

    calculate_scores(complaints);

    // Build Max-Heap
    int n = complaints.size();
    for (int i = n / 2 - 1; i >= 0; i--) heapify(complaints, n, i);

    // Extract ALL complaints so Python can handle pagination
    int total_complaints = complaints.size();
    for (int i = 0; i < total_complaints && !complaints.empty(); i++) {
        Complaint top = complaints[0];
        cout << top.id << "|" << top.room << "|" << top.category << "|" << top.score << endl;
        complaints[0] = complaints.back();
        complaints.pop_back();
        heapify(complaints, complaints.size(), 0);
    }

    return 0;
}