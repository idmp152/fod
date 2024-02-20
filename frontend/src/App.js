import { useEffect, useState } from 'react';
import './App.css';
import axios from 'axios';
import Card from './Card';

function App() {
  const LIMIT = 20;

  const [posts, setPosts] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [fetching, setFetching] = useState(true);
  const [feedEnded, setFeedEnded] = useState(false)

  useEffect(() => {
    if (fetching) {
      axios.get(`http://localhost/serving/requestFeed?page=${currentPage}&limit=${LIMIT}`).then(response => {
        setPosts([...posts, ...response.data])
        setCurrentPage(prevState => prevState + 1)
        setFeedEnded(response.data.length < LIMIT)
      }).finally(() => setFetching(false))
    }
  }, [fetching])

  useEffect(() => {
    document.addEventListener('scroll', scrollHandler)
    return function() {
      document.removeEventListener('scroll', scrollHandler)
    };
  }, [])

  const scrollHandler = (e) => {
    if (e.target.documentElement.scrollHeight - (e.target.documentElement.scrollTop + window.innerHeight) < 100 && !feedEnded) {
      setFetching(true)
    }
  }

  return (
    <div className="app">
      <div className="app__header">
        <img
          className="app__headerImage"
          src="logo.png"
          alt=""
        />
      </div>
      <div className="app__pinContainer">
        {posts.map(post =>
          <Card url={post.image_url} key={post.id}/>
        )}
      </div>
    </div>
  );
}

export default App;